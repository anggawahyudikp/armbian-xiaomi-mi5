"""Acceptance must reject faults, missing coverage and RTC jumps."""
import copy
import importlib.util
from pathlib import Path
import unittest
from concurrent.futures import ThreadPoolExecutor
import tempfile
import threading
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("soak", Path(__file__).resolve().parents[2] / "scripts/stability-soak.py")
soak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soak)
host_spec = importlib.util.spec_from_file_location("monitor", Path(__file__).resolve().parents[2] / "scripts/monitor-soak.py")
monitor = importlib.util.module_from_spec(host_spec)
host_spec.loader.exec_module(monitor)


def series():
    return [{"boot_id": "test", "uptime": 1000 + i * 120, "errors": [],
             "root_write_ok": True, "ext4_errors": 0,
             "services": dict.fromkeys(soak.SERVICES, "active"), "failed_units": [],
             "charger_online": True, "usb_type": "Unknown SDP [DCP] CDP",
             "battery": 80, "battery_temp_c": 30, "cpu_temp_c": 55,
             "wifi_ipv4": True, "http_ok": True, "container_running": True,
             "container_oom": False, "container_restarts": 0, "counter": i}
            for i in range(31)]


class AcceptanceTest(unittest.TestCase):
    def test_concurrent_root_probes_do_not_clobber_each_other_or_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / 'write-probe'
            existing.write_text('keep-existing-file')
            barrier = threading.Barrier(8)
            def read_together(path):
                barrier.wait(timeout=5)
                return Path(path).read_text()
            with patch.object(soak, 'read', side_effect=read_together), ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda value: soak.verify_root_write(root, value),
                                        [f'independent-{i}' for i in range(8)]))
            self.assertTrue(all(results))
            self.assertEqual(existing.read_text(), 'keep-existing-file')
            self.assertEqual(list(root.iterdir()), [existing])

    def test_failed_root_probe_cleans_up_its_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(soak, 'read', side_effect=OSError('read failed')):
                with self.assertRaises(OSError):
                    soak.verify_root_write(Path(directory), 'test')
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_complete_coverage_passes(self):
        self.assertEqual(soak.assess(series(), 1)["status"], "passed")

    def test_short_run_and_empty_log_do_not_pass(self):
        self.assertEqual(soak.assess(series()[:5], 1)["status"], "running")
        self.assertEqual(soak.assess([], 1)["status"], "running")

    def test_clock_jump_cannot_fake_elapsed_duration(self):
        samples = series()[:5]
        samples[0]["timestamp"] = "1970-01-01T00:00:00Z"
        samples[-1]["timestamp"] = "2030-01-01T00:00:00Z"
        self.assertEqual(soak.assess(samples, 1)["status"], "running")

    def test_reboot_or_sampling_gap_fails(self):
        for field, value in (("boot_id", "different"), ("uptime", 999999)):
            samples = series()
            samples[10][field] = value
            self.assertEqual(soak.assess(samples, 1)["status"], "failed")

    def test_storage_power_network_and_container_faults_fail(self):
        faults = {"root_write_ok": False, "ext4_errors": 1, "battery": 10,
                  "battery_temp_c": 44, "cpu_temp_c": 85, "charger_online": False,
                  "usb_type": "[SDP] DCP", "http_ok": False, "wifi_ipv4": False,
                  "container_running": False, "container_oom": True,
                  "container_restarts": 1, "failed_units": ["docker.service"],
                  "errors": ["timeout"], "services": {}}
        for field, value in faults.items():
            with self.subTest(field=field):
                samples = series()
                samples[10][field] = copy.deepcopy(value)
                self.assertEqual(soak.assess(samples, 1)["status"], "failed")

    def test_declining_battery_or_stalled_app_fails(self):
        samples = series()
        samples[-1]["battery"] = 70
        self.assertEqual(soak.assess(samples, 1)["status"], "failed")
        samples = series()
        for sample in samples:
            sample["counter"] = 0
        self.assertEqual(soak.assess(samples, 1)["status"], "failed")

    def test_missing_probe_fields_fail_closed(self):
        self.assertEqual(soak.assess([{}], 1)["status"], "failed")

    def test_malformed_counter_cannot_crash_the_assessor(self):
        samples = series()
        samples[0]["counter"] = None
        self.assertEqual(soak.assess(samples, 1)["status"], "failed")

    def test_independent_http_failure_blocks_success(self):
        samples = [{"probe": sample, "external_http_ok": True} for sample in series()]
        self.assertEqual(monitor.assess(samples, 1)["status"], "passed")
        samples[8]["external_http_ok"] = False
        self.assertEqual(monitor.assess(samples, 1)["status"], "failed")

    def test_independent_ssh_failure_blocks_success(self):
        samples = [{"probe": sample, "external_http_ok": True} for sample in series()]
        samples[8]["probe"] = {"errors": ["SSH timeout"]}
        report = monitor.assess(samples, 1)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["failures"][0]["reasons"], ["probe unavailable or incomplete"])
        self.assertFalse(any("storage error" in f["reasons"] for f in report["failures"]))


if __name__ == "__main__":
    unittest.main()
