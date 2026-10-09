#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath


HERE = Path(__file__).resolve().parent
DATA = HERE / "DO_NOT_SHARE"
MODIFICATIONS = HERE / "modifications"
CLIENT_APP = HERE / "RobloxVersion/RobloxPlayer.app"
MANIFEST = DATA / "modifications-manifest.json"
BACKUP = DATA / "modifications-backup"


def relative_path(value):
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
    ):
        raise ValueError("A modification path is invalid.")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"Unsafe modification path: {value}")
    return path


def safe_target(root, relative):
    root = root.resolve()
    target = root.joinpath(*relative.parts)
    if not target.resolve(strict=False).is_relative_to(root):
        raise ValueError(f"Modification path escapes its target: {relative}")

    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Refusing to follow a symlink: {current}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"Modification parent is not a directory: {current}")
    if target.is_symlink():
        raise ValueError(f"Refusing to replace a symlink: {target}")
    return target


def collect_modifications():
    if MODIFICATIONS.is_symlink():
        raise ValueError(f"The modifications folder cannot be a symlink: {MODIFICATIONS}")
    MODIFICATIONS.mkdir(mode=0o700, parents=True, exist_ok=True)
    files = []
    for directory, dirnames, filenames in os.walk(MODIFICATIONS, followlinks=False):
        directory_path = Path(directory)
        for dirname in dirnames:
            path = directory_path / dirname
            if path.is_symlink():
                raise ValueError(f"Modification folders cannot be symlinks: {path}")
        for filename in filenames:
            source = directory_path / filename
            if source.is_symlink() or not stat.S_ISREG(source.stat().st_mode):
                raise ValueError(f"Only regular files can be used as modifications: {source}")
            relative = PurePosixPath(source.relative_to(MODIFICATIONS).as_posix())
            relative_path(relative.as_posix())
            files.append((source, relative))
    return sorted(files, key=lambda item: item[1].as_posix())


def load_manifest():
    if not MANIFEST.exists():
        if BACKUP.exists():
            raise ValueError(
                f"Found a modification backup without its manifest: {BACKUP}"
            )
        return None

    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read the modification manifest: {error}") from error
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("The modification manifest has an unsupported format.")
    entries = payload.get("files")
    if not isinstance(entries, list):
        raise ValueError("The modification manifest has an invalid file list.")

    validated = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("The modification manifest contains an invalid entry.")
        relative = relative_path(entry.get("path"))
        had_original = entry.get("had_original")
        if not isinstance(had_original, bool):
            raise ValueError("The modification manifest contains an invalid backup record.")
        path = relative.as_posix()
        if path in seen:
            raise ValueError(f"The modification manifest repeats a path: {path}")
        seen.add(path)
        validated.append((relative, had_original))
    return validated


def copy_atomically(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=".mactolinux-mod-",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        shutil.copy2(source, temporary_path)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_manifest(entries):
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DATA,
            prefix=".modifications-",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(
                {
                    "version": 1,
                    "files": [
                        {"path": path.as_posix(), "had_original": had_original}
                        for path, had_original in entries
                    ],
                },
                temporary_file,
                indent=2,
            )
            temporary_file.write("\n")
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, MANIFEST)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def reset_modifications():
    entries = load_manifest()
    if entries is None:
        return False
    if not CLIENT_APP.is_dir():
        raise FileNotFoundError(
            f"Roblox client is not installed; cannot restore modifications: {CLIENT_APP}"
        )

    for relative, had_original in entries:
        target = safe_target(CLIENT_APP, relative)
        if had_original:
            backup = safe_target(BACKUP, relative)
            if not backup.is_file():
                raise ValueError(f"Original file backup is missing: {backup}")
            if target.exists() and not target.is_file():
                raise ValueError(f"Cannot restore over a non-file: {target}")
            copy_atomically(backup, target)
        elif target.exists():
            if not target.is_file():
                raise ValueError(f"Cannot remove a non-file modification: {target}")
            target.unlink()

    MANIFEST.unlink()
    try:
        shutil.rmtree(BACKUP)
    except FileNotFoundError:
        pass
    return True


def apply_modifications():
    files = collect_modifications()
    if not files:
        reset_modifications()
        return 0
    if not CLIENT_APP.is_dir():
        raise FileNotFoundError(f"Roblox client is not installed: {CLIENT_APP}")

    reset_modifications()
    if BACKUP.exists():
        raise ValueError(f"Refusing to overwrite an existing backup: {BACKUP}")
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)

    staging_backup = Path(
        tempfile.mkdtemp(prefix=".modifications-backup-", dir=DATA)
    )
    entries = []
    try:
        for source, relative in files:
            target = safe_target(CLIENT_APP, relative)
            if target.exists() and not target.is_file():
                raise ValueError(f"Cannot replace a non-file: {target}")
            had_original = target.exists()
            if had_original:
                backup_path = safe_target(staging_backup, relative)
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup_path)
            entries.append((relative, had_original))

        os.replace(staging_backup, BACKUP)
        write_manifest(entries)
    except (OSError, ValueError):
        if staging_backup.exists():
            shutil.rmtree(staging_backup)
        if BACKUP.exists() and not MANIFEST.exists():
            shutil.rmtree(BACKUP)
        raise

    try:
        for source, relative in files:
            target = safe_target(CLIENT_APP, relative)
            copy_atomically(source, target)
    except (OSError, ValueError) as error:
        try:
            reset_modifications()
        except (OSError, ValueError) as reset_error:
            raise RuntimeError(
                f"Could not apply modifications ({error}) or roll them back "
                f"({reset_error})."
            ) from error
        raise
    return len(files)


def main():
    parser = argparse.ArgumentParser(description="Manage Roblox client modifications.")
    parser.add_argument("action", choices=("reset",))
    parser.add_argument("--quiet", action="store_true")
    arguments = parser.parse_args()

    try:
        changed = reset_modifications()
    except (OSError, ValueError) as error:
        print(f"Could not reset Roblox modifications: {error}", file=sys.stderr)
        return 1
    if changed and not arguments.quiet:
        print("Restored Roblox client files and reset modifications.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
