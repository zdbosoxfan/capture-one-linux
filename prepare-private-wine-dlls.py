#!/usr/bin/env python3
"""Prepare known Fedora Wine 11 private copies; no installed file is changed.
SPDX-License-Identifier: MIT
"""
import hashlib
from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: prepare-private-wine-dlls.py RUNNER OUTPUT_DIRECTORY")
runner, output = map(Path, sys.argv[1:])
source = runner / "lib64/wine-wow64/wine/x86_64-windows"
specs = [
    ("mscms.dll", "mscms_wine.dll",
     "6a32f9d584f6bd389fa879e9a19973f9293e492a010d423f66e50862f2a6fee5",
     "b8b1a6d29ba5089fecd2d11af677dd652808d3b20d14a7b23ea26abf7d4da709"),
    ("wine-d3d9.dll", "d3d9.dll",
     "ce054a9fd408ab81c049f5bd7879758f31097774a3b991b52f328f07f6edc94b",
     "828ced6b5cf1581fe600134ab3b5f78600527a29d39130629e3b547ac0c59007"),
]
prepared = []
for name, target, expected_source, expected_output in specs:
    data = (source / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_source:
        raise SystemExit("Different Wine file; inspect before adapting: " + name)
    if data[0x40:0x51] != b"Wine builtin DLL\0":
        raise SystemExit("Expected Wine marker absent: " + name)
    if name == "mscms.dll":
        data = data[:0x40] + b"Wine private DLL\0" + data[0x51:]
    else:
        data = data[:0x40] + b"X" + data[0x41:]
    if hashlib.sha256(data).hexdigest() != expected_output:
        raise SystemExit("Unexpected private copy hash: " + name)
    if (output / target).exists() or (output / target).is_symlink():
        raise SystemExit("Refusing to replace output: " + target)
    prepared.append((output / target, data))
output.mkdir(parents=True, exist_ok=True)
for path, data in prepared:
    with path.open("xb") as f:
        f.write(data)
    print(path.name, hashlib.sha256(data).hexdigest())
