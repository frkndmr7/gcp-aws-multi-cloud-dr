"""Local packaging checks; no cloud or dependency downloads."""
import zipfile
from pathlib import Path

import pytest

from scripts.build_failback_zip import digest, verify_entries, wheel_member, write_archive


def test_wheel_paths_reject_traversal():
    for name in ("../outside", "/absolute/file", "pkg/../../outside"):
        with pytest.raises(ValueError):
            wheel_member(name)


def test_wheel_data_layout():
    assert wheel_member("pkg.data/purelib/module.py") == "module.py"
    assert wheel_member("pkg.data/platlib/module.so") == "module.so"
    assert wheel_member("pkg.data/scripts/tool") is None


def test_archive_is_deterministic_and_never_overwrites(tmp_path):
    a, b = tmp_path / "a.zip", tmp_path / "b.zip"
    write_archive(a, {"b": b"second", "a": b"first"})
    write_archive(b, {"a": b"first", "b": b"second"})
    assert digest(a.read_bytes()) == digest(b.read_bytes())
    with zipfile.ZipFile(a) as archive:
        assert archive.namelist() == ["a", "b"]
        assert archive.testzip() is None
        assert all(x.date_time == (2020, 1, 1, 0, 0, 0) for x in archive.infolist())
    with pytest.raises(FileExistsError):
        write_archive(a, {"x": b"new"})


def runtime_entries():
    names = ("functions/failback_identity/handler.py", "functions/failback_identity/probe.py",
             "google/auth/aws.py", "google/cloud/firestore_v1/client.py", "boto3/__init__.py")
    return {name: b"pass\n" for name in names}


def test_missing_runtime_dependency_rejected():
    with pytest.raises(ValueError, match="Missing handler"):
        verify_entries({})


@pytest.mark.parametrize("native", [b"not ELF", b"\x7fELF\x02\x01" + bytes(12) + (183).to_bytes(2, "little")])
def test_wrong_native_architecture_rejected(native):
    entries = runtime_entries()
    entries["native.so"] = native
    with pytest.raises(ValueError, match="Linux x86_64"):
        verify_entries(entries)


def test_native_architecture_and_sources_checked():
    entries = runtime_entries()
    entries["native.so"] = b"\x7fELF\x02\x01" + bytes(12) + (62).to_bytes(2, "little")
    assert verify_entries(entries) == 1
    entries["functions/failback_identity/handler.py"] = b"syntax error!"
    with pytest.raises(SyntaxError):
        verify_entries(entries)
