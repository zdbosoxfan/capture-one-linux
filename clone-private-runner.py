#!/usr/bin/env python3
"""Copy an installed Fedora Wine runtime into a NEW private directory.

SPDX-License-Identifier: MIT
No Wine process is launched; no prefix is opened; no source file is changed.
Uses cp --reflink=auto where supported, freezes external file symlinks, and
records source hashes. The result still uses the host's ordinary ELF libraries.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relative_to(path, parent):
    try:
        return path.relative_to(parent)
    except ValueError:
        return None


def walk_entries(root):
    # Include directory links without following them outside the source tree.
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            yield Path(directory) / name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--wine-tree", type=Path,
                        default=Path("/usr/lib64/wine-wow64/wine"))
    parser.add_argument("--wine-data", type=Path, default=Path("/usr/share/wine"))
    parser.add_argument("--wineserver", type=Path, default=Path("/usr/bin/wineserver64"))
    args = parser.parse_args()
    requested_destination = args.destination.expanduser()
    if requested_destination.exists() or requested_destination.is_symlink():
        parser.error("Destination must not exist; this helper never overwrites a runner.")
    destination = requested_destination.resolve()
    if destination.exists() or destination.is_symlink():
        parser.error("Destination must not exist; this helper never overwrites a runner.")
    sources = [args.wine_tree.resolve(strict=True), args.wine_data.resolve(strict=True)]
    targets = [destination / "lib64/wine-wow64/wine", destination / "share/wine"]
    server = args.wineserver.resolve(strict=True)
    for source in sources:
        if relative_to(destination, source) is not None:
            parser.error("Destination cannot be inside a source tree.")
    loader = sources[0] / "x86_64-unix/wine"
    ntdll = sources[0] / "x86_64-unix/ntdll.so"
    if not loader.is_file() or not ntdll.is_file() or not server.is_file():
        parser.error("Expected internal loader, ntdll.so and matching wineserver are missing.")

    # Preflight links first. Directory links outside the copied trees need
    # manual review; never recursively collect arbitrary host directories.
    links = []
    files = []
    for source, target in zip(sources, targets):
        for original in walk_entries(source):
            copied = target / original.relative_to(source)
            if original.is_symlink():
                resolved = original.resolve(strict=True)
                private_target = None
                for source2, target2 in zip(sources, targets):
                    relative = relative_to(resolved, source2)
                    if relative is not None:
                        private_target = target2 / relative
                        break
                if private_target is None:
                    if not resolved.is_file():
                        parser.error("External directory link requires manual review: " + str(original))
                    private_target = destination / "frozen-dependencies" / (digest(resolved) + "-" + resolved.name)
                links.append((original, copied, resolved, private_target))
            elif original.is_file():
                files.append((original, copied))

    destination.mkdir(parents=True)
    for source, target in zip(sources, targets):
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-a", "--reflink=auto", str(source), str(target)], check=True)
    (destination / "bin").mkdir()
    shutil.copy2(server, destination / "bin/wineserver")
    records = []
    for original, copied, resolved, private_target in links:
        if relative_to(private_target, destination / "frozen-dependencies") is not None:
            private_target.parent.mkdir(exist_ok=True)
            if not private_target.exists():
                shutil.copy2(resolved, private_target)
        copied.unlink()
        copied.symlink_to(os.path.relpath(private_target, copied.parent))
        records.append({"path": str(copied.relative_to(destination)),
                        "source_link": str(original), "source_resolved": str(resolved),
                        "private_target": os.readlink(copied)})

    checksums = []
    for original, copied in files + [(server, destination / "bin/wineserver")]:
        expected = digest(original)
        if digest(copied) != expected:
            raise RuntimeError("Copied file hash mismatch: " + str(copied))
        checksums.append({"path": str(copied.relative_to(destination)),
                          "source": str(original), "sha256": expected})
    for original, copied, resolved, private_target in links:
        if copied.is_file() and digest(copied) != digest(resolved):
            raise RuntimeError("Frozen link hash mismatch: " + str(copied))
        if relative_to(copied.resolve(strict=True), destination.resolve()) is None:
            raise RuntimeError("Link still resolves outside runner: " + str(copied))

    # Critical loader pair must be independent real files, not system links.
    for critical in [targets[0] / "x86_64-unix/wine", targets[0] / "x86_64-unix/ntdll.so"]:
        if critical.is_symlink():
            data = critical.resolve(strict=True)
            critical.unlink()
            shutil.copy2(data, critical)
    manifest = {"source_only_helper": True, "prefix_launched": False,
                "source_modified": False, "files": checksums, "frozen_links": records}
    (destination / "clone-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Created private runner:", destination)
    print("Verified regular files:", len(checksums), "; frozen links:", len(records))
    print("No prefix or application was launched. Apply only the matched pair of rebuilt modules.")


if __name__ == "__main__":
    main()
