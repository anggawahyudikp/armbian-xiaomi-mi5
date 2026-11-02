#!/usr/bin/env python3
"""Collect the RAM diagnostic shell on a specific USB port; never reboot/flash.

Only opens a 0525:a4a7 gadget on the requested physical USB port. Waits for the
Gemini diagnostic banner before sending fixed, read-only inspection commands.
Existing laptop ACM devices (for example a WWAN modem) are left alone.
"""
import argparse
import datetime
import json
import os
import pathlib
import select
import sys
import termios
import time
import tty


def gadget_port(usb_port):
    for entry in pathlib.Path('/sys/class/tty').glob('ttyACM*'):
        device = (entry / 'device').resolve()
        for parent in device.parents:
            if parent.name != usb_port:
                continue
            try:
                identity = tuple((parent / name).read_text().strip().lower()
                                 for name in ('idVendor', 'idProduct'))
            except OSError:
                continue
            if identity == ('0525', 'a4a7'):
                return pathlib.Path('/dev') / entry.name
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--usb-port', required=True, help='Physical USB path, e.g. 2-1')
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--timeout', type=float, default=180)
    args = parser.parse_args()
    if args.timeout <= 0 or '/' in args.usb_port:
        parser.error('Use a positive timeout and a USB port name, not a filesystem path')
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'usb_port': args.usb_port, 'gadget_detected': False,
              'diagnostic_banner_seen': False, 'inspection_completed': False,
              'device_rebooted': False, 'partitions_flashed': False}
    deadline = time.monotonic() + args.timeout
    descriptor, original = None, None
    data = bytearray()
    try:
        while time.monotonic() < deadline:
            port = gadget_port(args.usb_port)
            if port is not None:
                descriptor = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
                original = termios.tcgetattr(descriptor)
                tty.setraw(descriptor)
                settings = termios.tcgetattr(descriptor)
                settings[4] = settings[5] = termios.B115200
                termios.tcsetattr(descriptor, termios.TCSANOW, settings)
                report.update(gadget_detected=True, serial_port=str(port))
                print('Opened verified Gemini USB gadget:', port, flush=True)
                break
            time.sleep(0.5)
        if descriptor is None:
            report['result'] = 'No matching USB ACM gadget before timeout'
            return 1
        with (args.output / 'console.log').open('wb') as stream:
            while time.monotonic() < deadline:
                readable, _, _ = select.select([descriptor], [], [], min(0.5, max(0, deadline - time.monotonic())))
                if not readable:
                    continue
                chunk = os.read(descriptor, 65536)
                if not chunk:
                    break
                stream.write(chunk)
                stream.flush()
                data.extend(chunk)
                normalized = bytes(data).replace(b'\r', b'')
                if not report['diagnostic_banner_seen'] and b'Gemini diagnostic\n' in normalized:
                    report['diagnostic_banner_seen'] = True
                    # No mount, block-device write, network configuration, or reboot.
                    # Clear a partial input line left by early console echo.
                    # Ctrl-U avoids sending a signal while ash is starting.
                    command = (b"\x15\ngemini-diagnostics; printf '\\nMI5_FULL_DMESG_BEGIN\\n'; "
                               b"dmesg; printf '\\nMI5_DIAGNOSTICS_END\\n'\n")
                    os.write(descriptor, command)
                    print('Diagnostic shell confirmed; collecting read-only summary and dmesg', flush=True)
                if b'\nMI5_DIAGNOSTICS_END\n' in normalized:
                    report['inspection_completed'] = True
                    break
        report['console_bytes'] = len(data)
        report['result'] = 'Inspection complete' if report['inspection_completed'] else 'Console incomplete before disconnect/timeout'
        return 0 if report['inspection_completed'] else 1
    except OSError as exc:
        report['result'] = str(exc)
        return 1
    finally:
        if descriptor is not None:
            try:
                if original is not None:
                    termios.tcsetattr(descriptor, termios.TCSANOW, original)
            except termios.error:
                pass
            os.close(descriptor)
        report['finished_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (args.output / 'console-report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    sys.exit(main())
