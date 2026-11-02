#!/usr/bin/python3
"""LCD idle blanking and power-key handling; never suspend the server."""
import argparse
import glob
import json
import os
from pathlib import Path
import selectors
import signal
import socket
import struct
import time

CONFIG = Path('/etc/default/mi5-console')
RUNTIME = Path('/run/mi5-console')
EVENT = struct.Struct('@llHHI')


def load_config(path=CONFIG):
    values = {'SLEEP_SECONDS': 300, 'BRIGHTNESS_PERCENT': 20}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            key, separator, value = line.partition('=')
            if not separator or key.strip() not in values:
                raise ValueError('Unknown console setting: ' + line)
            values[key.strip()] = int(value.strip())
    if not 0 <= values['SLEEP_SECONDS'] <= 86400:
        raise ValueError('SLEEP_SECONDS must be 0..86400 (0 disables timeout)')
    if not 1 <= values['BRIGHTNESS_PERCENT'] <= 100:
        raise ValueError('BRIGHTNESS_PERCENT must be 1..100')
    return values


class LCD:
    def __init__(self, sysroot=Path('/sys')):
        self.sysroot = sysroot

    def set_awake(self, awake, brightness):
        blank = self.sysroot / 'class/graphics/fb0/blank'
        devices = [p for p in (self.sysroot / 'class/backlight').glob('*')
                   if not any(word in p.name for word in ('button', 'kbd', 'keyboard'))]
        if not blank.exists() or not devices:
            raise RuntimeError('LCD framebuffer/backlight is not available')
        # Use backlight blanking for sleep. The current Gemini DSI workaround
        # retains analog power across DPMS; avoid unnecessary modesets on idle.
        if awake:
            blank.write_text('0\n')
        for device in devices:
            maximum = int((device / 'max_brightness').read_text())
            value = max(1, maximum * brightness // 100) if awake else 0
            (device / 'brightness').write_text(str(value) + '\n')


class IdleController:
    def __init__(self, lcd, config, clock=time.monotonic):
        self.lcd, self.config, self.clock = lcd, config, clock
        self.awake = None
        self.last_activity = clock()
        self.set_awake(True)

    def set_awake(self, awake):
        self.lcd.set_awake(awake, self.config['BRIGHTNESS_PERCENT'])
        self.awake = awake
        if awake:
            self.last_activity = self.clock()

    def event(self, kind, code, value):
        if kind == 1 and code == 116:  # KEY_POWER: press only, not release/repeat
            if value == 1:
                self.set_awake(not self.awake)
        elif kind == 1 and value == 1 or kind == 3:
            if not self.awake:
                self.set_awake(True)
            self.last_activity = self.clock()

    def tick(self):
        timeout = self.config['SLEEP_SECONDS']
        if self.awake and timeout and self.clock() - self.last_activity >= timeout:
            self.set_awake(False)


def daemon():
    RUNTIME.mkdir(mode=0o755, exist_ok=True)
    address = RUNTIME / 'control.sock'
    address.unlink(missing_ok=True)
    control = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    control.bind(str(address))
    os.chmod(address, 0o600)
    selector = selectors.DefaultSelector()
    selector.register(control, selectors.EVENT_READ, 'control')
    inputs, buffers = {}, {}
    state = IdleController(LCD(), load_config())
    running, last_scan, previous = True, -10, None

    def stop(_signum, _frame):
        nonlocal running
        running = False

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, stop)
    try:
        while running:
            now = time.monotonic()
            if now - last_scan >= 10:
                last_scan = now
                for path in glob.glob('/dev/input/event*'):
                    if path in inputs:
                        continue
                    try:
                        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
                        selector.register(fd, selectors.EVENT_READ, path)
                        inputs[path], buffers[fd] = fd, b''
                    except OSError as exc:
                        print(f'Input {path}: {exc}', flush=True)
            for key, _mask in selector.select(timeout=1):
                if key.data == 'control':
                    command = control.recv(64).decode().strip()
                    try:
                        if command == 'reload':
                            config = load_config()
                            state.config = config
                            state.set_awake(state.awake)
                        elif command in ('wake', 'sleep'):
                            state.set_awake(command == 'wake')
                    except (ValueError, OSError) as exc:
                        print(f'Console command rejected: {exc}', flush=True)
                else:
                    try:
                        data = os.read(key.fd, EVENT.size * 64)
                    except OSError:
                        data = b''
                    if not data:
                        selector.unregister(key.fd)
                        os.close(key.fd)
                        inputs.pop(key.data, None)
                        buffers.pop(key.fd, None)
                        continue
                    data = buffers[key.fd] + data
                    while len(data) >= EVENT.size:
                        _sec, _usec, kind, code, value = EVENT.unpack_from(data)
                        state.event(kind, code, value)
                        data = data[EVENT.size:]
                    buffers[key.fd] = data
            state.tick()
            status = {'awake': state.awake, 'sleep_seconds': state.config['SLEEP_SECONDS'],
                      'brightness_percent': state.config['BRIGHTNESS_PERCENT'],
                      'input_devices': len(inputs)}
            if status != previous:
                temporary = RUNTIME / 'status.tmp'
                temporary.write_text(json.dumps(status) + '\n')
                temporary.replace(RUNTIME / 'status.json')
                print(json.dumps(status), flush=True)
                if previous is None and os.environ.get('NOTIFY_SOCKET'):
                    target = os.environ['NOTIFY_SOCKET']
                    if target.startswith('@'):
                        target = '\0' + target[1:]
                    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notify:
                        notify.connect(target)
                        notify.send(b'READY=1')
                previous = status
    finally:
        for fd in inputs.values():
            os.close(fd)
        selector.close()
        control.close()
        address.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('daemon', 'wake', 'sleep', 'reload', 'status'))
    args = parser.parse_args()
    if args.command == 'daemon':
        daemon()
    elif args.command == 'status':
        print((RUNTIME / 'status.json').read_text(), end='')
    else:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as connection:
            connection.connect(str(RUNTIME / 'control.sock'))
            connection.send(args.command.encode())


if __name__ == '__main__':
    main()
