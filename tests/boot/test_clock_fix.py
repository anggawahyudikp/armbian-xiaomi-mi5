"""Guard the upstream FD AHB fix against unintended or partial source edits."""
from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'scripts/apply-msm8996-clock-fix.py'
spec = importlib.util.spec_from_file_location('clock_fix', HELPER)
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)
SOURCE = """static const unsigned int unrelated = 0x3ba74;
static struct clk_branch fd_ahb_clk = {
    .halt_reg = 0x3ba74,
    .clkr = {
        .enable_reg = 0x3ba74,
        .enable_mask = BIT(0),
    },
};
static const struct regmap_config config = {
    .max_register = 0xb008,
};
"""


class ClockFixTest(unittest.TestCase):
    def test_both_registers_fixed_and_unrelated_value_preserved(self):
        result = fix.corrected_source(SOURCE)
        self.assertIn('.halt_reg = 0x3b74,', result)
        self.assertIn('.enable_reg = 0x3b74,', result)
        self.assertIn('unrelated = 0x3ba74;', result)
        self.assertEqual(result.count('0x3ba74'), 1)

    def test_already_fixed_source_is_idempotent(self):
        result = fix.corrected_source(SOURCE)
        self.assertEqual(fix.corrected_source(result), result)

    def test_known_partial_fix_is_completed(self):
        partial = SOURCE.replace('.halt_reg = 0x3ba74', '.halt_reg = 0x3b74')
        self.assertEqual(fix.corrected_source(partial), fix.corrected_source(SOURCE))

    def test_unknown_halt_register_rejected(self):
        with self.assertRaises(ValueError):
            fix.corrected_source(SOURCE.replace('.halt_reg = 0x3ba74', '.halt_reg = 0x1234'))

    def test_unknown_enable_register_rejected(self):
        with self.assertRaises(ValueError):
            fix.corrected_source(SOURCE.replace('.enable_reg = 0x3ba74', '.enable_reg = 0x1234'))

    def test_missing_or_duplicate_branch_rejected(self):
        for text in (SOURCE.replace('fd_ahb_clk', 'other_clk'), SOURCE + SOURCE):
            with self.subTest(text=text), self.assertRaises(ValueError):
                fix.corrected_source(text)

    def test_register_outside_configured_range_rejected(self):
        with self.assertRaises(ValueError):
            fix.corrected_source(SOURCE.replace('0xb008', '0x1000'))

    def test_cli_failure_does_not_partially_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / fix.RELATIVE
            path.parent.mkdir(parents=True)
            bad = SOURCE.replace('.enable_reg = 0x3ba74', '.enable_reg = 0x1234')
            path.write_text(bad)
            result = subprocess.run([sys.executable, str(HELPER), directory], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_text(), bad)

    def test_cli_check_and_repeat_preserve_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / fix.RELATIVE
            path.parent.mkdir(parents=True)
            path.write_text(SOURCE)
            command = [sys.executable, str(HELPER), directory]
            check = subprocess.run(command + ['--check'], capture_output=True)
            self.assertNotEqual(check.returncode, 0)
            self.assertEqual(path.read_text(), SOURCE)
            subprocess.run(command, capture_output=True, check=True)
            before = path.stat().st_mtime_ns
            subprocess.run(command, capture_output=True, check=True)
            subprocess.run(command + ['--check'], capture_output=True, check=True)
            self.assertEqual(path.stat().st_mtime_ns, before)


if __name__ == '__main__':
    unittest.main()
