#!/usr/bin/env python3
"""Import a built ZIP inside a Python 3.12/Linux x86_64 container; deny networking."""
import argparse
import importlib
import json
from pathlib import Path, PurePosixPath
import platform
import sys
import tempfile
import zipfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12) or platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        parser.error("Run inside CPython 3.12 / Linux x86_64; host imports are insufficient")

    def deny_network(event, arguments):
        if event in ("socket.connect", "socket.getaddrinfo"):
            raise RuntimeError("Network use is forbidden during import verification")

    sys.addaudithook(deny_network)
    with tempfile.TemporaryDirectory(prefix="failback-import-") as directory:
        with zipfile.ZipFile(args.package) as archive:
            for name in archive.namelist():
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("Unsafe archive path")
            archive.extractall(directory)
        sys.path.insert(0, directory)
        handler = importlib.import_module("functions.failback_identity.handler")
        probe = importlib.import_module("functions.failback_identity.probe")
        importlib.import_module("google.auth.aws")
        importlib.import_module("google.cloud.firestore")
        importlib.import_module("grpc")
        assert callable(handler.handler) and callable(probe.run_probe)
        assert Path(handler.__file__).resolve().is_relative_to(Path(directory).resolve())
        print(json.dumps({"target": "CPython 3.12/Linux x86_64", "handler_import": "ok", "network": "denied"}))


if __name__ == "__main__":
    main()
