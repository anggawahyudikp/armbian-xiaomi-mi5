#!/usr/bin/env python3
"""Write deterministic newc+gzip with root ownership, including device nodes."""
import gzip
import os
import pathlib
import stat
import sys

root, output = map(pathlib.Path, sys.argv[1:])
with output.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as archive:
    inode = 0

    def entry(name, mode, data=b"", rmajor=0, rminor=0):
        global inode
        inode += 1
        name_bytes = name.encode() + b"\0"
        fields = [inode, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, 0,
                  len(data), 0, 0, rmajor, rminor, len(name_bytes), 0]
        header = b"070701" + "".join(f"{n:08x}" for n in fields).encode()
        archive.write(header + name_bytes)
        archive.write(b"\0" * (-(110 + len(name_bytes)) % 4))
        archive.write(data)
        archive.write(b"\0" * (-len(data) % 4))

    entry(".", stat.S_IFDIR | 0o755)
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(dirs + files):
            path = pathlib.Path(directory) / name
            rel = path.relative_to(root).as_posix()
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                data = os.readlink(path).encode()
            elif stat.S_ISREG(info.st_mode):
                data = path.read_bytes()
            elif stat.S_ISDIR(info.st_mode):
                data = b""
            else:
                raise SystemExit(f"Unsupported file in initramfs: {rel}")
            entry(rel, info.st_mode, data)
    for name, major, minor, mode in [("console", 5, 1, 0o600), ("null", 1, 3, 0o666)]:
        entry("dev/" + name, stat.S_IFCHR | mode, rmajor=major, rminor=minor)
    entry("TRAILER!!!", 0)
