#!/usr/bin/env python3
"""Validate Mi 5 board data and stage it in a rootfs/initramfs or local input file."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from wifi_board import PROFILE, SOURCE, TARGET, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--source', type=Path, default=None)
    source.add_argument('--modem-image', type=Path,
                        help='Read image/bdwlan30.bin from a backed-up modem FAT image using mcopy')
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument('--destination-root', type=Path)
    destination.add_argument('--output', type=Path)
    destination.add_argument('--check', action='store_true', help='Validate the build input without writing files')
    args = parser.parse_args()
    try:
        if args.modem_image:
            with tempfile.TemporaryDirectory(prefix='mi5-board-') as directory:
                extracted = Path(directory) / 'bdwlan30.bin'
                subprocess.run(['mcopy', '-i', str(args.modem_image.resolve()),
                                '::/image/bdwlan30.bin', str(extracted)], check=True, timeout=30)
                data = extracted.read_bytes()
        else:
            data = (args.source or SOURCE).read_bytes()
        digest = validate(data)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'{exc}\nSee docs/wifi-board-data.md for the required device firmware input.\n')
    if args.check:
        print(f'Verified Mi 5 Wi-Fi board data: {digest} ({PROFILE["bytes"]} bytes)')
        return
    output = args.output if args.output else args.destination_root / TARGET
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as temporary:
        temporary.write(data)
        name = Path(temporary.name)
    try:
        name.chmod(0o644)
        os.replace(name, output)
    finally:
        name.unlink(missing_ok=True)
    print(f'Verified Mi 5 Wi-Fi board data: {digest} ({PROFILE["bytes"]} bytes)')


if __name__ == '__main__':
    main()
