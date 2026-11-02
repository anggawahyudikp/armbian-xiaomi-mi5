"""Diagnostics must tolerate missing hardware and avoid publishing identifiers."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[2] / 'rootfs-overlay/usr/local/lib/mi5/health.py'
spec = importlib.util.spec_from_file_location('health', path)
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


class HealthTest(unittest.TestCase):
    def test_missing_hardware_and_commands(self):
        with patch.object(health, 'read', return_value=None), patch.object(health, 'command', return_value=None), patch.object(health.Path, 'glob', return_value=[]):
            result = health.snapshot()
            self.assertNotIn('addresses', result)
            self.assertNotIn('boot_id', result)
            self.assertIn('Battery: ?%', health.summary(result))

    def test_default_does_not_query_ip_or_identifiers(self):
        with patch.object(health, 'command', return_value=None) as command:
            result = health.snapshot()
            self.assertFalse(any(call.args[0][0] == 'ip' for call in command.call_args_list))
            self.assertNotIn('boot_id', result)
            self.assertNotIn('addresses', result)

    def test_command_timeout_is_nonfatal(self):
        with patch.object(health.subprocess, 'run', side_effect=health.subprocess.TimeoutExpired('systemctl', 3)):
            self.assertIsNone(health.command(['systemctl', 'is-active', 'docker']))
