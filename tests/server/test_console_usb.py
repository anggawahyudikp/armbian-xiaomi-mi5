#!/usr/bin/env python3
"""Exercise idle/power events and USB management isolation without hardware."""
import importlib.util
import ipaddress
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
def module(name):
    path = ROOT / ('rootfs-overlay/usr/local/lib/mi5/' + name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
console, usb, wifi = module('console'), module('usb_gadget'), module('wifi_ready')

class ConsoleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.blank = self.root / 'class/graphics/fb0/blank'
        self.blank.parent.mkdir(parents=True)
        self.blank.write_text('0')
        self.light = self.root / 'class/backlight/wled'
        self.light.mkdir(parents=True)
        (self.light / 'max_brightness').write_text('4095')
        (self.light / 'brightness').write_text('0')
        self.cpu = self.root / 'devices/system/cpu/cpu2/online'
        self.cpu.parent.mkdir(parents=True)
        self.cpu.write_text('1')
        self.now = 0
        self.state = console.IdleController(console.LCD(self.root),
            {'SLEEP_SECONDS': 300, 'BRIGHTNESS_PERCENT': 20}, lambda: self.now)

    def test_idle_sleeps_and_power_wakes_without_offlining_cpu(self):
        self.now = 300
        self.state.tick()
        self.assertFalse(self.state.awake)
        self.assertEqual((self.light/'brightness').read_text(), '0\n')
        self.assertEqual(self.cpu.read_text(), '1')
        self.state.event(1, 116, 1)
        self.assertTrue(self.state.awake)
        self.assertEqual((self.light/'brightness').read_text(), '819\n')
        self.state.event(1, 116, 2)
        self.state.event(1, 116, 0)
        self.assertTrue(self.state.awake)

    def test_disabled_timeout_and_local_activity(self):
        self.state.config['SLEEP_SECONDS'] = 0
        self.now = 99999
        self.state.tick()
        self.assertTrue(self.state.awake)
        self.state.set_awake(False)
        self.state.event(3, 53, 100)
        self.assertTrue(self.state.awake)

    def test_config_rejects_zero_brightness_and_unknown_keys(self):
        path = self.root/'config'
        for content in ('BRIGHTNESS_PERCENT=0', 'SLEEP_SECONDS=-1', 'TYPO=3'):
            path.write_text(content)
            with self.assertRaises(ValueError): console.load_config(path)

class USBTest(unittest.TestCase):
    def test_switching_modes_does_not_reuse_windows_os_descriptor_cache(self):
        for order in (('ncm', 'rndis'), ('rndis', 'ncm')):
            cache = {}
            for mode in order:
                descriptor = usb.device_descriptor_values(mode)
                key = tuple(int(descriptor[name], 0) for name in
                            ('idVendor', 'idProduct', 'bcdDevice'))
                # Windows retains both successful and failed OS-string queries.
                # NCM has no Microsoft OS string; RNDIS needs its compatible ID.
                if key not in cache:
                    cache[key] = mode == 'rndis'
                self.assertEqual(cache[key], mode == 'rndis',
                                 'Previous USB mode poisoned OS-descriptor discovery')

    def test_modes_do_not_reuse_the_legacy_shared_descriptor_cache(self):
        for mode in ('rndis', 'ncm'):
            descriptor = usb.device_descriptor_values(mode)
            self.assertNotEqual(int(descriptor['bcdDevice'], 0), 0x0101)

    def test_unique_stable_unicast_addresses(self):
        first = usb.identity('0'*32)
        self.assertEqual(first, usb.identity('0'*32))
        self.assertNotEqual(first, usb.identity('1'*32))
        self.assertNotEqual(first[0], first[1])
        for mac in first:
            self.assertEqual(int(mac[:2], 16) & 3, 2)
        with self.assertRaises(ValueError): usb.identity('')

    def test_dhcp_does_not_advertise_gateway_dns_or_lease_phone_address(self):
        for own in (2, 15, 110, 210):
            address = ipaddress.IPv4Interface(f'192.168.7.{own}/24')
            config = usb.dhcp_config(address)
            self.assertIn('port=0\n', config)
            self.assertIn('interface=usb0\n', config)
            self.assertIn('dhcp-option=option:router\n', config)
            self.assertIn('dhcp-option=option:dns-server\n', config)
            line = next(line for line in config.splitlines() if line.startswith('dhcp-range='))
            low, high, *_ = line.split('=', 1)[1].split(',')
            self.assertFalse(ipaddress.IPv4Address(low) <= address.ip <= ipaddress.IPv4Address(high))

    def test_unknown_mode_and_nonprivate_address_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config'
            for text in ('MODE=ecm', 'ADDRESS=8.8.8.8/24', 'ADDRESS=192.168.7.0/24'):
                path.write_text(text)
                with self.assertRaises(ValueError): usb.settings(path)

class LifecycleTest(unittest.TestCase):
    def test_os_shutdown_does_not_rebind_or_restart_serial(self):
        with mock.patch.object(usb, 'run', return_value=SimpleNamespace(stdout='stopping\n')) as run, \
             mock.patch.object(usb, 'remove_gadget') as remove, \
             mock.patch.object(usb, 'restore_legacy') as restore:
            usb.stop()
            remove.assert_not_called()
            restore.assert_not_called()
            self.assertEqual(run.call_count, 1)
            run.reset_mock()
            usb.serial_ready()
            self.assertEqual(run.call_count, 1)

    def test_serial_restart_waits_for_replaced_device_events(self):
        with mock.patch.object(usb, 'manager_stopping', return_value=False), \
             mock.patch.object(usb, 'run') as run:
            usb.serial_ready()
            self.assertEqual(run.call_args_list, [
                mock.call('udevadm', 'settle', '--timeout=10'),
                mock.call('systemctl', '--no-block', 'restart',
                          'serial-getty@ttyGS0.service', check=False)])

    def test_unsettled_device_events_do_not_start_getty(self):
        with mock.patch.object(usb, 'manager_stopping', return_value=False), \
             mock.patch.object(usb, 'run', side_effect=RuntimeError('udev timeout')) as run:
            with self.assertRaisesRegex(RuntimeError, 'udev timeout'):
                usb.serial_ready()
            run.assert_called_once_with('udevadm', 'settle', '--timeout=10')

    def test_normal_stop_restores_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp);(state/'legacy-device').write_text('gadget.0')
            with mock.patch.object(usb, 'STATE', state), \
                 mock.patch.object(usb, 'run', return_value=SimpleNamespace(stdout='running\n')), \
                 mock.patch.object(usb, 'remove_gadget') as remove, \
                 mock.patch.object(usb, 'restore_legacy') as restore:
                usb.stop()
                remove.assert_called_once()
                restore.assert_called_once_with('gadget.0')
                self.assertFalse((state/'legacy-device').exists())

class WiFiEnumerationTest(unittest.TestCase):
    def test_late_endpoint_recovers_after_rescan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);port=root/'devices/0000:00:00.0';port.mkdir(parents=True)
            (port/'vendor').write_text('0x17cb');(port/'rescan').write_text('')
            endpoint=root/'devices/0000:01:00.0';now=[0]
            def sleep(delay):
                now[0]+=delay
                if now[0]>=1:
                    endpoint.mkdir(exist_ok=True)
                    (endpoint/'vendor').write_text('0x168c');(endpoint/'device').write_text('0x003e')
            scans=wifi.ensure_wifi(root, clock=lambda:now[0], sleep=sleep)
            self.assertEqual(scans,2)
            self.assertEqual((port/'rescan').read_text(),'1\n')
            self.assertEqual(wifi.ensure_wifi(root),0)

    def test_missing_endpoint_has_bounded_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            now=[0]
            def sleep(delay):now[0]+=delay
            with self.assertRaises(RuntimeError):
                wifi.ensure_wifi(Path(tmp),timeout=2,clock=lambda:now[0],sleep=sleep)
            self.assertEqual(now[0],2)

    def test_unexpected_root_port_not_touched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);port=root/'devices/0000:00:00.0';port.mkdir(parents=True)
            (port/'vendor').write_text('0xffff');(port/'rescan').write_text('untouched')
            with self.assertRaises(RuntimeError):wifi.ensure_wifi(root)
            self.assertEqual((port/'rescan').read_text(),'untouched')

if __name__ == '__main__': unittest.main()
