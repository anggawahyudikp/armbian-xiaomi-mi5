#!/usr/bin/python3
"""Bounded retry for one explicitly selected server Wi-Fi profile."""
import json
import os
from pathlib import Path
import re
import subprocess
import time

CONFIG = Path('/etc/default/mi5-wifi-recovery')
STATE = Path('/run/mi5-wifi-recovery/state.json')


def run(*args):
    result = subprocess.run(['nmcli', '--wait', '40', *args], capture_output=True,
                            text=True, timeout=45, env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        raise RuntimeError('nmcli operation failed')
    return result.stdout.strip()


def eligible(radio, state, reason, autoconnect):
    # Never interrupt activation, connected links, a disabled radio or user disconnect.
    return radio == 'enabled' and state == 30 and reason != 39 and autoconnect == 'yes'


def due(state, now, ready):
    attempts = [stamp for stamp in state.get('attempts', []) if 0 <= now - stamp < 3600]
    state['attempts'] = attempts
    if not ready:
        state.pop('down_since', None)
        return False
    start = state.setdefault('down_since', now)
    return now - start >= 600 and len(attempts) < 3 and (not attempts or now - attempts[-1] >= 600)


def main():
    config = dict(line.split('=', 1) for line in CONFIG.read_text().splitlines()
                  if line and not line.startswith('#'))
    uuid = config.get('PROFILE_UUID', '')
    if not uuid:
        return
    if not re.fullmatch(r'[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}', uuid):
        raise ValueError('PROFILE_UUID must be a UUID')
    interface = config.get('INTERFACE', 'wlan0')
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,15}', interface):
        raise ValueError('Invalid INTERFACE')
    if run('-g', 'connection.type', 'connection', 'show', 'uuid', uuid) != '802-11-wireless':
        raise ValueError('Selected profile is not Wi-Fi')
    radio = run('radio', 'wifi')
    status = int(run('-g', 'GENERAL.STATE', 'device', 'show', interface).split()[0])
    reason = int(run('-g', 'GENERAL.REASON', 'device', 'show', interface).split()[0])
    automatic = run('-g', 'connection.autoconnect', 'connection', 'show', 'uuid', uuid)
    device_auto = run('-g', 'GENERAL.AUTOCONNECT', 'device', 'show', interface)
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = {}
    now = time.monotonic()
    retry = due(state, now, eligible(radio, status, reason, automatic) and device_auto == 'yes')
    if retry:
        # Charge the budget before attempting, including failures/timeouts.
        state['attempts'].append(now)
    STATE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(state) + '\n')
    temporary.chmod(0o600)
    temporary.replace(STATE)
    if retry:
        print('Retrying configured Wi-Fi profile; bounded to 3 attempts/hour', flush=True)
        run('connection', 'up', 'uuid', uuid, 'ifname', interface)


if __name__ == '__main__':
    main()
