#!/usr/bin/env python3
"""Prevent generic or corrupt board data from silently returning to Mi 5 images."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from wifi_board import PROFILE, validate


class WifiBoardTest(unittest.TestCase):
    def test_previous_generic_fallback_is_rejected(self):
        old = ROOT / 'rootfs-overlay/usr/lib/firmware/ath10k/QCA6174/hw3.0/board.bin'
        if not old.is_file():
            self.skipTest('Optional legacy firmware fixture is not distributed; synthetic rejection tests remain mandatory')
        with self.assertRaisesRegex(ValueError, 'Unverified Wi-Fi board data'):
            validate(old.read_bytes())

    def test_same_length_and_valid_internal_checksum_do_not_prove_identity(self):
        data = bytes.fromhex('ffff') + bytes(PROFILE['bytes'] - 2)
        with self.assertRaisesRegex(ValueError, 'Unverified Wi-Fi board data'):
            validate(data)

    def test_truncation_and_corruption_are_rejected(self):
        for data in (b'', bytes(PROFILE['bytes'])):
            with self.assertRaises(ValueError):
                validate(data)

    def test_rejected_input_does_not_overwrite_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = [Path(directory) / name for name in ('bad.bin', 'output.bin')]
            source.write_bytes(bytes(PROFILE['bytes']))
            output.write_bytes(b'keep-existing-file')
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/prepare-wifi-board.py'),
                                     '--source', str(source), '--output', str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), b'keep-existing-file')


if __name__ == '__main__':
    unittest.main()
