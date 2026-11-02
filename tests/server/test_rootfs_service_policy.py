import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("service_policy", Path(__file__).resolve().parents[2] / "scripts/rootfs_service_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class ServicePolicyTest(unittest.TestCase):
    def test_build_stub_removed_and_cleanup_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usr/sbin/policy-rc.d"
            path.parent.mkdir(parents=True)
            path.write_text("#!/bin/sh\nexit 101\n")
            self.assertTrue(policy.cleanup(directory))
            self.assertFalse(path.exists())
            self.assertFalse(policy.cleanup(directory))

    def test_custom_policy_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usr/sbin/policy-rc.d"
            path.parent.mkdir(parents=True)
            data = "#!/bin/sh\ncase $1 in cron) exit 101;; *) exit 0;; esac\n"
            path.write_text(data)
            self.assertFalse(policy.cleanup(directory))
            self.assertEqual(path.read_text(), data)

    def test_symlink_target_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "custom-policy"
            target.write_text("#!/bin/sh\nexit 101\n")
            path = Path(directory) / "usr/sbin/policy-rc.d"
            path.parent.mkdir(parents=True)
            path.symlink_to(target)
            self.assertFalse(policy.cleanup(directory))
            self.assertTrue(path.is_symlink())
            self.assertTrue(target.exists())
