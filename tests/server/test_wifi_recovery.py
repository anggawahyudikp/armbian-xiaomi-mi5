import importlib.util
from pathlib import Path
import unittest
import tempfile
import json
from unittest.mock import patch

path = Path(__file__).resolve().parents[2] / 'rootfs-overlay/usr/local/lib/mi5/wifi_recover.py'
spec = importlib.util.spec_from_file_location('wifi_recover', path)
wifi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi)


class RecoveryTest(unittest.TestCase):
    def test_never_interrupt_active_connection_or_user_choice(self):
        for state in (10, 20, 40, 50, 60, 70, 80, 90, 100, 110, 120):
            self.assertFalse(wifi.eligible('enabled', state, 0, 'yes'))
        self.assertFalse(wifi.eligible('disabled', 30, 0, 'yes'))
        self.assertFalse(wifi.eligible('enabled', 30, 39, 'yes'))
        self.assertFalse(wifi.eligible('enabled', 30, 0, 'no'))
        self.assertTrue(wifi.eligible('enabled', 30, 0, 'yes'))

    def test_wait_and_budget_including_failed_attempts(self):
        state = {}
        self.assertFalse(wifi.due(state, 0, True))
        for now in (600, 1200, 1800):
            self.assertTrue(wifi.due(state, now, True))
            state['attempts'].append(now)
            self.assertFalse(wifi.due(state, now + 1, True))
        self.assertFalse(wifi.due(state, 3000, True))
        self.assertTrue(wifi.due(state, 4200, True))

    def test_recovery_resets_wait_but_preserves_retry_budget(self):
        state = {'down_since': 0, 'attempts': [600]}
        self.assertFalse(wifi.due(state, 700, False))
        self.assertNotIn('down_since', state)
        self.assertEqual(state['attempts'], [600])
        self.assertFalse(wifi.due(state, 1500, True))

    def test_failed_activation_charges_budget_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config'
            state = Path(directory) / 'state.json'
            config.write_text('PROFILE_UUID=00000000-0000-0000-0000-000000000001\n')
            state.write_text('{"down_since": 0, "attempts": []}')
            def run(*args):
                if args[:2] == ('connection', 'up'):
                    self.assertEqual(json.loads(state.read_text())['attempts'], [700])
                    raise RuntimeError('activation failed')
                if args == ('radio', 'wifi'): return 'enabled'
                return {'connection.type': '802-11-wireless', 'GENERAL.STATE': '30 (disconnected)',
                        'GENERAL.REASON': '0 (none)', 'connection.autoconnect': 'yes',
                        'GENERAL.AUTOCONNECT': 'yes'}[args[1]]
            with patch.object(wifi, 'CONFIG', config), patch.object(wifi, 'STATE', state), \
                 patch.object(wifi.time, 'monotonic', return_value=700), patch.object(wifi, 'run', side_effect=run):
                with self.assertRaises(RuntimeError): wifi.main()
            self.assertEqual(json.loads(state.read_text())['attempts'], [700])
