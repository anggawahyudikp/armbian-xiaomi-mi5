#!/usr/bin/python3
"""Read-only, allowlisted Mi 5 health snapshots. No profiles, credentials or logs."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess


def read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, ValueError):
        return None


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=3,
                                env={**os.environ, 'LC_ALL': 'C'})
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def snapshot(private=False):
    supplies = {}
    for path in Path('/sys/class/power_supply').glob('*'):
        supplies[path.name] = {field: read(path / field) for field in (
            'type', 'status', 'capacity', 'current_now', 'voltage_now', 'temp',
            'online', 'usb_type', 'input_current_limit') if (path / field).exists()}
    thermal = {}
    for path in Path('/sys/class/thermal').glob('thermal_zone*'):
        thermal[path.name] = {'type': read(path / 'type'), 'millidegrees_c': read(path / 'temp')}
    interfaces = {}
    for path in Path('/sys/class/net').glob('*'):
        interfaces[path.name] = {'state': read(path / 'operstate'), 'carrier': read(path / 'carrier')}
    wifi = {}
    for name in interfaces:
        if (Path('/sys/class/net') / name / 'wireless').exists():
            link = command(['iw', 'dev', name, 'link']) or ''
            wifi[name] = {key: value.strip() for line in link.splitlines()
                          if ':' in line for key, value in [line.strip().split(':', 1)]
                          if key in ('signal', 'tx bitrate', 'rx bitrate', 'freq')}
    services = {name: command(['systemctl', 'is-active', name]) or 'inactive-or-unavailable'
                for name in ('NetworkManager', 'ssh', 'docker', 'mi5-console', 'mi5-usb-gadget')}
    disk = shutil.disk_usage('/')
    console = read('/run/mi5-console/status.json')
    try:
        console = json.loads(console) if console else None
    except ValueError:
        console = None
    data = {'timestamp': datetime.now(timezone.utc).isoformat(),
            'kernel': os.uname().release, 'uptime_seconds': (read('/proc/uptime') or '').split(' ')[0],
            'load': read('/proc/loadavg'), 'power': supplies, 'thermal': thermal,
            'interfaces': interfaces, 'wifi': wifi, 'services': services, 'console': console,
            'root_bytes': {'total': disk.total, 'free': disk.free},
            'power_irq': [line.strip() for line in (read('/proc/interrupts') or '').splitlines()
                          if 'pm8941_pwrkey' in line],
            'memory': {line.split(':')[0]: line.split(':')[1].strip()
                       for line in (read('/proc/meminfo') or '').splitlines()
                       if line.startswith(('MemAvailable:', 'MemTotal:', 'SwapTotal:', 'SwapFree:'))}}
    if private:
        data['boot_id'] = read('/proc/sys/kernel/random/boot_id')
        data['addresses'] = command(['ip', '-brief', 'address'])
    return data


def summary(data):
    power = data['power'].get('qcom-battery', {})
    disk = data['root_bytes']
    lines = ['Armbian for Xiaomi Mi 5 | community preview',
             f"Battery: {power.get('capacity', '?')}% ({power.get('status', 'unknown')}) | "
             f"Root free: {disk['free'] / 2**30:.1f} GiB",
             'Services: ' + ' | '.join(f'{k}={v}' for k, v in data['services'].items()),
             'Interfaces: ' + ' | '.join(f"{k}={v['state']}" for k, v in data['interfaces'].items()
                                        if k != 'lo'),
             'Settings: mi5-config | Diagnostics: mi5-doctor --json']
    temperatures = [f"{zone['type']}={int(zone['millidegrees_c']) / 1000:.1f}C"
                    for zone in sorted(data['thermal'].values(), key=lambda item: (not str(item['type']).startswith('cpu'), str(item['type'])))
                    if zone['millidegrees_c'] and zone['millidegrees_c'].lstrip('-').isdigit()]
    if temperatures:
        lines.insert(2, 'Temperature: ' + ' | '.join(temperatures[:4]))
    if data.get('addresses'):
        lines.append(data['addresses'])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--private', action='store_true', help='Include local IP addresses and boot ID; do not publish unreviewed')
    parser.add_argument('--record', action='store_true', help='Append private snapshot to bounded root-only history')
    args = parser.parse_args()
    if args.record and os.geteuid() != 0:
        parser.error('--record requires root')
    data = snapshot(args.private or args.record)
    if args.record:
        directory = Path('/var/lib/mi5-health')
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.chmod(0o700)
        path = directory / 'samples.jsonl'
        if path.exists() and path.stat().st_size >= 2 * 1024 * 1024:
            path.replace(directory / 'samples.previous.jsonl')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(json.dumps(data, sort_keys=True) + '\n')
    else:
        print(json.dumps(data, indent=2, sort_keys=True) if args.json else summary(data))


if __name__ == '__main__':
    main()
