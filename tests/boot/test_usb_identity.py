"""A composite Linux gadget must never be accepted as LK fastboot."""
import pathlib
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
from usb_identity import lk_serials, select_lk


class UsbIdentityTest(unittest.TestCase):
    def device(self, root, name, vendor, product, serial):
        node = root / name
        node.mkdir()
        for key, value in (('idVendor', vendor), ('idProduct', product), ('serial', serial)):
            (node / key).write_text(value + '\n')

    def test_linux_composite_is_not_lk(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            self.device(root, '2-1', '1d6b', '0104', 'PHONE')
            self.assertEqual(lk_serials(root), [])

    def test_expected_usb_identity_and_serial_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            self.device(root, '2-1', '18d1', 'd00d', 'PHONE')
            self.assertEqual(select_lk(lk_serials(root), 'PHONE'), 'PHONE')
            self.assertIsNone(select_lk(lk_serials(root), 'OTHER'))

    def test_multiple_devices_require_explicit_selection(self):
        with self.assertRaisesRegex(ValueError, 'Multiple'):
            select_lk(['FIRST', 'SECOND'])
        self.assertEqual(select_lk(['FIRST', 'SECOND'], 'SECOND'), 'SECOND')

    def test_disappearing_nodes_and_malformed_serials_are_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / 'removed').mkdir()
            self.device(root, '2-1', '18d1', 'd00d', 'BAD\nSERIAL')
            self.assertEqual(lk_serials(root), [])

    def test_host_script_rejects_misleading_fastboot_devices_output(self):
        with tempfile.TemporaryDirectory() as folder:
            setup = pathlib.Path(folder) / 'shell-functions'
            setup.write_text('''
python3() { return 1; }
fastboot() { printf 'PHONE\\177\\n'; }
ping() { return 1; }
ssh() { echo 'Unexpected SSH execution' >&2; return 1; }
lsusb() { return 0; }
''')
            result = subprocess.run(
                ['bash', str(pathlib.Path(__file__).resolve().parents[2] / 'scripts/reboot-fastboot.sh')],
                env={**os.environ, 'BASH_ENV': str(setup), 'WAIT_SEC': '0'},
                capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 1)
            self.assertIn('no fastboot device', result.stderr)
            self.assertNotIn('Unexpected SSH execution', result.stderr)


if __name__ == '__main__':
    unittest.main()
