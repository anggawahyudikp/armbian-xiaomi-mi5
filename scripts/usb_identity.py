#!/usr/bin/env python3
"""Find an enumerated LK USB bootloader independently of fastboot text output."""
import argparse
from pathlib import Path
import re


def lk_serials(root=Path('/sys/bus/usb/devices')):
    if not root.is_dir():
        raise OSError('Linux USB sysfs is required for verified LK detection')
    found = set()
    for device in root.iterdir():
        try:
            identity = tuple((device / name).read_text().strip().lower()
                             for name in ('idVendor', 'idProduct'))
            if identity != ('18d1', 'd00d'):
                continue
            serial = (device / 'serial').read_text().strip()
        except OSError:
            continue
        if re.fullmatch(r'[A-Za-z0-9_-]{1,64}', serial):
            found.add(serial)
    return sorted(found)


def select_lk(serials, expected=None):
    if expected:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', expected):
            raise ValueError('Invalid PHONE_SERIAL')
        return expected if expected in serials else None
    if len(serials) > 1:
        raise ValueError('Multiple LK devices; set PHONE_SERIAL to the intended phone')
    return serials[0] if serials else None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial', default='')
    a = p.parse_args()
    try:
        serial = select_lk(lk_serials(), a.serial)
    except (OSError, ValueError) as exc:
        p.exit(2, str(exc) + '\n')
    if serial:
        print(serial)
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
