#!/usr/bin/python3
"""One composite network+ACM gadget; Wi-Fi remains the default route."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import time

CONFIG = Path('/etc/default/mi5-usb')
GADGET = Path('/sys/kernel/config/usb_gadget/mi5')
STATE = Path('/run/mi5-usb')
LEGACY = Path('/sys/bus/gadget/drivers/g_serial')


def settings(path=CONFIG):
    values = {'MODE': 'rndis', 'ADDRESS': '192.168.7.2/24'}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            key, sep, value = line.partition('=')
            if not sep or key.strip() not in values:
                raise ValueError('Unknown USB setting: ' + line)
            values[key.strip()] = value.strip()
    if values['MODE'] not in ('rndis', 'ncm'):
        raise ValueError('MODE must be rndis or ncm')
    address = ipaddress.IPv4Interface(values['ADDRESS'])
    if address.network.prefixlen != 24 or not address.ip.is_private:
        raise ValueError('ADDRESS must be a private IPv4 /24 address')
    if address.ip in (address.network.network_address, address.network.broadcast_address):
        raise ValueError('ADDRESS must be a host address')
    return values, address


def identity(machine_id):
    if len(machine_id) != 32 or any(c not in '0123456789abcdef' for c in machine_id):
        raise ValueError('A generated machine-id is required before USB setup')
    def mac(role):
        raw = bytearray(hashlib.sha256((machine_id + role).encode()).digest()[:6])
        raw[0] = (raw[0] & 0xfc) | 0x02
        return ':'.join(f'{n:02x}' for n in raw)
    return mac('host'), mac('device')


def device_descriptor_values(mode):
    # Windows caches OS-descriptor availability by VID/PID/revision. Both
    # layouts must have their own revision, newer than shared legacy 0x0101.
    revisions = {'rndis': '0x0102', 'ncm': '0x0103'}
    if mode not in revisions:
        raise ValueError('Unsupported USB descriptor mode')
    return {'idVendor': '0x1d6b', 'idProduct': '0x0104',
            'bcdUSB': '0x0200', 'bcdDevice': revisions[mode],
            'bDeviceClass': '0xef', 'bDeviceSubClass': '0x02',
            'bDeviceProtocol': '0x01'}


def dhcp_config(address):
    # Empty router/DNS options suppress dnsmasq's defaults. This is a local
    # management cable, not an Internet gateway for the attached computer.
    base = int(address.network.network_address)
    for start, end in ((10, 30), (100, 120), (200, 220)):
        first, last = ipaddress.IPv4Address(base + start), ipaddress.IPv4Address(base + end)
        if not first <= address.ip <= last:
            break
    return '\n'.join((
        'port=0', 'no-resolv', 'bind-interfaces', 'interface=usb0',
        'except-interface=lo', 'dhcp-authoritative',
        f'dhcp-range={first},{last},255.255.255.0,1h',
        'dhcp-option=option:router', 'dhcp-option=option:dns-server',
        'dhcp-leasefile=/run/mi5-usb-dhcp/leases', 'log-facility=-', ''))


def run(*args, check=True):
    return subprocess.run(args, check=check, text=True, capture_output=True)


def write(path, value):
    path.write_text(str(value) + '\n')


def legacy_device():
    devices = list(Path('/sys/bus/gadget/devices').glob('*'))
    for device in devices:
        driver = device / 'driver'
        if driver.is_symlink() and driver.resolve().name == 'g_serial':
            return device.name
    return None


def restore_legacy(name):
    if name and (LEGACY / 'bind').exists():
        try:
            write(LEGACY / 'bind', name)
        except OSError as exc:
            print('Legacy ACM restore:', exc, flush=True)


def remove_gadget():
    if not GADGET.exists():
        return
    bound = (GADGET / 'UDC').read_text().strip()
    if bound:
        write(GADGET / 'UDC', '')
    # Configfs attributes are virtual: remove only links and directories.
    links = [p for p in GADGET.rglob('*') if p.is_symlink()]
    for path in sorted(links, key=lambda p: len(p.parts), reverse=True):
        path.unlink()
    # Remove user-created groups only; configfs default groups disappear
    # automatically when their owning function/gadget is removed.
    for relative in ('configs/c.1/strings/0x409', 'configs/c.1',
                     'functions/acm.usb0', 'functions/rndis.usb0',
                     'functions/ncm.usb0', 'strings/0x409'):
        path = GADGET / relative
        if path.exists():
            path.rmdir()
    GADGET.rmdir()


def start():
    values, address = settings()
    STATE.mkdir(mode=0o755, exist_ok=True)
    if not os.path.ismount('/sys/kernel/config'):
        run('mount', '-t', 'configfs', 'none', '/sys/kernel/config')
    if GADGET.exists():
        raise RuntimeError('Mi 5 gadget already exists; stop it before reconfiguration')
    machine_id = Path('/etc/machine-id').read_text().strip()
    host_mac, device_mac = identity(machine_id)
    legacy = legacy_device()
    (STATE / 'legacy-device').write_text(legacy or '')
    try:
        if legacy:
            write(LEGACY / 'unbind', legacy)
        GADGET.mkdir()
        descriptors = device_descriptor_values(values['MODE'])
        for name, value in descriptors.items():
            write(GADGET / name, value)
        strings = GADGET / 'strings/0x409'
        strings.mkdir()
        write(strings / 'serialnumber', machine_id + '-' + values['MODE'])
        write(strings / 'manufacturer', 'Armbian community')
        write(strings / 'product', 'Armbian for Xiaomi Mi 5')
        config = GADGET / 'configs/c.1'
        config.mkdir()
        (config / 'strings/0x409').mkdir(parents=True)
        write(config / 'strings/0x409/configuration', values['MODE'].upper() + '+ACM')
        write(config / 'MaxPower', 500)
        write(config / 'bmAttributes', '0x80')
        function = GADGET / ('functions/' + values['MODE'] + '.usb0')
        function.mkdir()
        write(function / 'host_addr', host_mac)
        write(function / 'dev_addr', device_mac)
        write(function / 'ifname', 'usb%d')
        if values['MODE'] == 'rndis':
            for name, value in {'class': '0xef', 'subclass': '0x04', 'protocol': '0x01'}.items():
                write(function / name, value)
            descriptor = function / 'os_desc/interface.rndis'
            write(descriptor / 'compatible_id', 'RNDIS')
            write(descriptor / 'sub_compatible_id', '5162001')
            write(GADGET / 'os_desc/use', 1)
            write(GADGET / 'os_desc/b_vendor_code', '0xcd')
            write(GADGET / 'os_desc/qw_sign', 'MSFT100')
            (GADGET / 'os_desc/c.1').symlink_to(config)
        (config / function.name).symlink_to(function)
        acm = GADGET / 'functions/acm.usb0'
        acm.mkdir()
        # Allocate and verify ACM first line so existing ttyGS0 getty remains valid.
        if int((acm / 'port_num').read_text()) != 0:
            raise RuntimeError('ACM did not receive ttyGS0; refusing ambiguous serial setup')
        (config / acm.name).symlink_to(acm)
        udcs = list(Path('/sys/class/udc').glob('*'))
        if len(udcs) != 1:
            raise RuntimeError('Expected exactly one Mi 5 USB device controller')
        write(GADGET / 'UDC', udcs[0].name)
        for _ in range(100):
            if Path('/sys/class/net/usb0').exists():
                break
            time.sleep(0.1)
        if (function / 'ifname').read_text().strip() != 'usb0':
            raise RuntimeError('Unexpected gadget interface name; leaving other interfaces untouched')
        run('ip', 'link', 'set', 'dev', 'usb0', 'up')
        run('ip', '-4', 'addr', 'replace', str(address), 'dev', 'usb0')
        (STATE / 'dnsmasq.conf').write_text(dhcp_config(address))
        (STATE / 'status.json').write_text(json.dumps({
            'mode': values['MODE'], 'device_revision': descriptors['bcdDevice'],
            'address': str(address), 'interface': 'usb0',
            'host_mac': host_mac, 'device_mac': device_mac,
            'internet_gateway': False}) + '\n')
        print('USB management ready:', values['MODE'], str(address), flush=True)
    except Exception:
        try:
            remove_gadget()
        finally:
            restore_legacy(legacy)
        raise


def manager_stopping():
    return run('systemctl', 'is-system-running', check=False).stdout.strip() == 'stopping'


def serial_ready():
    if not manager_stopping():
        # Replacing legacy g_serial reuses ttyGS0. Its delayed remove event can
        # stop the new getty through BindsTo= after it has already started.
        # Drain device events before queuing an authenticated login prompt.
        run('udevadm', 'settle', '--timeout=10')
        run('systemctl', '--no-block', 'restart', 'serial-getty@ttyGS0.service', check=False)


def stop():
    # Keep the working composite/console bound until kernel shutdown. Rebinding
    # a legacy console and starting a getty during OS teardown is unnecessary.
    if manager_stopping():
        print('System stopping: leave USB bound for kernel shutdown', flush=True)
        return
    run('systemctl', 'stop', 'serial-getty@ttyGS0.service', check=False)
    remove_gadget()
    marker = STATE / 'legacy-device'
    restore_legacy(marker.read_text().strip() if marker.exists() else '')
    for name in ('status.json', 'dnsmasq.conf', 'legacy-device'):
        (STATE / name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('start', 'stop', 'status', 'serial-ready'))
    args = parser.parse_args()
    if args.command == 'start':
        start()
    elif args.command == 'stop':
        stop()
    elif args.command == 'serial-ready':
        serial_ready()
    else:
        print((STATE / 'status.json').read_text(), end='')


if __name__ == '__main__':
    main()
