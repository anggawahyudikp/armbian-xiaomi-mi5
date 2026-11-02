#!/usr/bin/python3
"""Bounded boot-time enumeration of the Mi 5's late QCA6174 endpoint."""
from pathlib import Path
import time


def ensure_wifi(root=Path('/sys/bus/pci'), timeout=20, clock=time.monotonic, sleep=time.sleep):
    port = root / 'devices/0000:00:00.0'
    endpoint = root / 'devices/0000:01:00.0'
    deadline, scans = clock() + timeout, 0
    while True:
        if (endpoint / 'vendor').exists():
            if (endpoint / 'vendor').read_text().strip() != '0x168c' or (endpoint / 'device').read_text().strip() != '0x003e':
                raise RuntimeError('Unexpected PCIe endpoint; refusing to treat it as Mi 5 Wi-Fi')
            print(f'Mi 5 Wi-Fi PCIe endpoint ready after {scans} rescans', flush=True)
            return scans
        if clock() >= deadline:
            raise RuntimeError('QCA6174 did not enumerate within the boot recovery window')
        if (port / 'rescan').exists():
            if (port / 'vendor').read_text().strip() != '0x17cb':
                raise RuntimeError('Unexpected PCIe root port; refusing rescan')
            (port / 'rescan').write_text('1\n')
            scans += 1
        sleep(0.5)


if __name__ == '__main__':
    ensure_wifi()
