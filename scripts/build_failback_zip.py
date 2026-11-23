#!/usr/bin/env python3
"""Build a deterministic CPython 3.12/Linux x86_64 failback Lambda ZIP.

Use --wheelhouse for an offline build. No cloud APIs, Terraform, or Git are used.
A successful build verifies layout and ELF architecture, not runtime imports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements-failback.txt"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wheel_member(name: str) -> str | None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe wheel path")
    parts = path.parts
    if parts and parts[0].endswith(".data"):
        if len(parts) < 3 or parts[1] not in ("purelib", "platlib"):
            return None  # Installation scripts are not Lambda runtime dependencies.
        return str(PurePosixPath(*parts[2:]))
    return str(path)


def archive_entries(wheels: Path) -> dict[str, bytes]:
    entries: dict[str, bytes] = {}
    for wheel in sorted(wheels.glob("*.whl")):
        if not (wheel.name.endswith("-none-any.whl") or "manylinux" in wheel.name and "x86_64" in wheel.name):
            raise ValueError("Wheel is not suitable for Linux x86_64")
        with zipfile.ZipFile(wheel) as source:
            for info in source.infolist():
                name = wheel_member(info.filename)
                if info.is_dir() or name is None:
                    continue
                content = source.read(info)
                if name in entries and entries[name] != content:
                    raise ValueError("Conflicting dependency files")
                entries[name] = content
    for relative in ("functions/__init__.py", "functions/failback_identity/__init__.py",
                     "functions/failback_identity/handler.py", "functions/failback_identity/probe.py"):
        entries[relative] = (ROOT / relative).read_bytes()
    return entries


def verify_entries(entries: dict[str, bytes]) -> int:
    required = ("functions/failback_identity/handler.py", "functions/failback_identity/probe.py",
                "google/auth/aws.py", "google/cloud/firestore_v1/client.py", "boto3/__init__.py")
    if not all(name in entries for name in required):
        raise ValueError("Missing handler or runtime dependencies")
    for name in required[:2]:
        compile(entries[name], name, "exec")
    native = 0
    for name, data in entries.items():
        if name.endswith(".so"):
            # ELF64 little endian, EM_X86_64. Does not execute the native library.
            if data[:6] != b"\x7fELF\x02\x01" or int.from_bytes(data[18:20], "little") != 62:
                raise ValueError("Native dependency is not Linux x86_64")
            native += 1
    if native == 0:
        raise ValueError("Expected gRPC/native dependencies are missing")
    return native


def write_archive(output: Path, entries: dict[str, bytes]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    # Do not overwrite previous release/rollback packages.
    with output.open("xb") as stream:
        with zipfile.ZipFile(stream, "w") as archive:
            for name, data in sorted(entries.items()):
                info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data, compresslevel=9)
    os.chmod(output, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, help="existing wheel directory; disables index/network access")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Output already exists; use a new release path")
    with tempfile.TemporaryDirectory(prefix="mcdr-failback-build-") as temp:
        wheels = Path(temp) / "wheels"
        command = [sys.executable, "-m", "pip", "download", "--disable-pip-version-check",
                   "--require-hashes", "--no-deps", "--only-binary=:all:",
                   "--platform", "manylinux2014_x86_64", "--implementation", "cp",
                   "--python-version", "3.12", "--abi", "cp312", "--dest", str(wheels),
                   "-r", str(LOCK)]
        if args.wheelhouse:
            command.extend(["--no-index", "--find-links", str(args.wheelhouse.resolve())])
        subprocess.run(command, check=True)
        entries = archive_entries(wheels)
        native = verify_entries(entries)
        manifest = {"target": "CPython 3.12 / Linux x86_64", "requirements_sha256": digest(LOCK.read_bytes()),
                    "wheels": {p.name: digest(p.read_bytes()) for p in sorted(wheels.glob("*.whl"))},
                    "sources": {name: digest(data) for name, data in entries.items() if name.startswith("functions/")}}
        entries["BUILD_MANIFEST.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
        write_archive(output, entries)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP checksum failure")
    print(json.dumps({"output": str(output), "sha256": digest(output.read_bytes()),
                      "bytes": output.stat().st_size, "native_linux_x86_64_files": native,
                      "runtime_import_test": "not performed by this script"}, sort_keys=True))


if __name__ == "__main__":
    main()
