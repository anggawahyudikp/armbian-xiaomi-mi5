import hashlib
import importlib.util
import json
import pathlib
import struct
import subprocess
import tempfile
import unittest
import sys
import gzip
import io
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).resolve().parents[2] / "scripts/fastboot-install.py"
sys.path.insert(0, str(SOURCE.parent))
from boot_layout import wrap_kernel, PROFILE, KERNEL_ADDRESS, RAMDISK_ADDRESS, DTB_ADDRESS
spec = importlib.util.spec_from_file_location("installer", SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerPreflight(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = pathlib.Path(self.temporary.name)
        inner = struct.pack("<2I6Q2I", 0xd503201f, 0x14000000, 0, 4096, 10,
                            0, 0, 0, 0x644d5241, 0).ljust(4096, b'\0')
        payload = gzip.compress(wrap_kernel(inner)) + struct.pack('>2I', 0xd00dfeed, 8)
        header = struct.pack("<8s9I", b"ANDROID!", len(payload), KERNEL_ADDRESS,
                             4096, RAMDISK_ADDRESS, 0, 0x84F00000, DTB_ADDRESS, 4096, 0)
        payload = payload.ljust((len(payload)+4095)//4096*4096,b'\0')
        (self.directory / "boot.img").write_bytes(header.ljust(4096,b'\0') + payload + bytes(4096))
        (self.directory / "rootfs.img").write_bytes(bytes(65536))
        self.checksums()
        self.calls = []
        self.product = "gemini"
        self.devices = "PHONE\tfastboot\n"
        self.unlocked = "yes"
        self.boot_capacity = "0x04000000"
        self.max_download = "0x10000000"
        self.oem_fallback = False
        self.version = "fastboot version 37.0.1-15733141"
        self.flash_code = 0
        self.default_proof = self.directory / 'device-proof.json'
        self.default_proof.write_text(json.dumps({'device':'gemini','serial':'PHONE',
                                                  'aboot_sha256':PROFILE['aboot_sha256']}))

    def tearDown(self):
        self.temporary.cleanup()

    def checksums(self):
        (self.directory / "SHA256SUMS").write_text("".join(
            hashlib.sha256((self.directory / name).read_bytes()).hexdigest() + "  " + name + "\n"
            for name in ("boot.img", "rootfs.img")))

    def fastboot(self, command, **kwargs):
        self.calls.append(command[1:])
        arguments = command[1:]
        code = 0
        if arguments == ["--version"]:
            text = self.version
        elif arguments == ["devices"]:
            text = self.devices
        elif "getvar" in arguments:
            name = arguments[-1]
            value = {"product": self.product, "unlocked": self.unlocked,
                     "partition-size:boot": self.boot_capacity,
                     "partition-size:userdata": "0x600000000",
                     "max-download-size": self.max_download}[name]
            if (name == "unlocked" and self.oem_fallback) or (name == "max-download-size" and value is None):
                text, code = "unknown variable", 1
            else:
                text = f"(bootloader) {name}: {value}\n"
        elif arguments[-2:] == ["oem", "device-info"]:
            text = "(bootloader) Device unlocked: true\n" if self.oem_fallback else "Device unlocked: false"
        else:
            text = "OKAY\n"
        return subprocess.CompletedProcess(command, code, stdout=text, stderr="")

    def run_installer(self, *extra, proof=True):
        if proof and '--device-proof' not in extra:
            extra = (*extra, '--device-proof', str(self.default_proof))
        owner = self
        class FlashProcess:
            def __init__(self, command, **kwargs):
                owner.calls.append(command[1:])
                self.stdout = io.StringIO("Sending sparse payload OKAY\nWriting payload OKAY\n")
            def __enter__(self): return self
            def __exit__(self, *args): self.stdout.close()
            def wait(self): return owner.flash_code
        with patch.object(installer.shutil, "which", return_value="mock-fastboot"), \
             patch.object(installer.subprocess, "run", side_effect=self.fastboot), \
             patch.object(installer.subprocess, "Popen", FlashProcess):
            return installer.main(["--directory", str(self.directory), "--yes", *extra])

    def assert_no_writes(self):
        self.assertFalse(any("flash" in call or "reboot" in call for call in self.calls))

    def test_old_or_unrecognized_client_never_flashes(self):
        for version in ("fastboot version 34.0.5", "unknown client"):
            with self.subTest(version=version):
                self.version = version
                with self.assertRaises(ValueError): self.run_installer()
                self.assert_no_writes()

    def test_failed_userdata_flash_never_writes_boot_or_reboots(self):
        self.flash_code = 1
        with self.assertRaises(ValueError): self.run_installer()
        writes = [call for call in self.calls if "flash" in call]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][writes[0].index("flash") + 1], "userdata")
        self.assertFalse(any("reboot" in call for call in self.calls))

    def test_missing_boot_never_contacts_device(self):
        (self.directory / "boot.img").unlink()
        with self.assertRaises(ValueError): self.run_installer()
        self.assertEqual(self.calls, [])

    def test_corrupt_payload_never_contacts_device(self):
        (self.directory / "rootfs.img").write_bytes(b"broken")
        with self.assertRaises(ValueError): self.run_installer()
        self.assertEqual(self.calls, [])

    def test_wrong_product_never_flashes(self):
        self.product = "lithium"
        with self.assertRaises(ValueError): self.run_installer()
        self.assert_no_writes()

    def test_locked_bootloader_never_flashes(self):
        self.unlocked = "no"
        with self.assertRaises(ValueError): self.run_installer()
        self.assert_no_writes()

    def test_oversized_boot_never_flashes(self):
        self.boot_capacity = "0x1000"
        with self.assertRaises(ValueError): self.run_installer()
        self.assert_no_writes()

    def test_ambiguous_devices_never_flashes(self):
        self.devices += "OTHER\tfastboot\n"
        with self.assertRaises(ValueError): self.run_installer()
        self.assert_no_writes()

    def test_success_checks_both_sizes_before_first_write(self):
        self.assertEqual(self.run_installer(), 0)
        first_write = next(i for i, call in enumerate(self.calls) if "flash" in call)
        self.assertIn(["-s", "PHONE", "getvar", "partition-size:boot"], self.calls[:first_write])
        self.assertIn(["-s", "PHONE", "getvar", "partition-size:userdata"], self.calls[:first_write])
        self.assertIn(["-s", "PHONE", "getvar", "max-download-size"], self.calls[:first_write])
        partitions = [call[call.index("flash") + 1] for call in self.calls if "flash" in call]
        self.assertEqual(partitions, ["userdata", "boot"])
        self.assertEqual(self.calls[-1], ["-s", "PHONE", "reboot"])

    def test_smaller_download_limit_caps_every_transfer(self):
        self.max_download = "0x02000000"
        self.assertEqual(self.run_installer(), 0)
        writes = [call for call in self.calls if "flash" in call]
        self.assertEqual(len(writes), 2)
        for call in writes:
            self.assertEqual(call[call.index("-S") + 1], str(32 * 1024 * 1024))

    def test_missing_download_limit_never_flashes(self):
        self.max_download = None
        with self.assertRaises(ValueError): self.run_installer()
        self.assert_no_writes()

    def test_invalid_download_limit_never_flashes(self):
        for value in ("0", "-1", "unknown", "0x100000000"):
            with self.subTest(value=value):
                self.calls = []
                self.max_download = value
                with self.assertRaises(ValueError): self.run_installer()
                self.assert_no_writes()

    def test_boot_larger_than_download_limit_never_flashes(self):
        self.max_download = str((self.directory / "boot.img").stat().st_size - 1)
        with self.assertRaises(ValueError): self.run_installer()
        self.assert_no_writes()

    def test_exact_boot_download_boundary_uses_raw_boot(self):
        self.max_download = str((self.directory / "boot.img").stat().st_size)
        self.assertEqual(self.run_installer(), 0)
        for call in [call for call in self.calls if "flash" in call]:
            self.assertEqual(call[call.index("-S") + 1], self.max_download)

    def test_decimal_download_limit_is_accepted(self):
        self.max_download = str(64 * 1024 * 1024)
        self.assertEqual(self.run_installer(), 0)
        for call in [call for call in self.calls if "flash" in call]:
            self.assertEqual(call[call.index("-S") + 1], "64M")

    def test_mi5_oem_unlock_query_fallback(self):
        self.oem_fallback = True
        self.assertEqual(self.run_installer(), 0)

    def test_generic_platform_product_requires_device_proof(self):
        self.product = "MSM8996"
        with self.assertRaises(ValueError): self.run_installer(proof=False)
        self.assert_no_writes()

    def test_generic_product_rejects_another_serials_proof(self):
        self.product = "MSM8996"
        proof = self.directory / "metadata.json"
        proof.write_text(json.dumps({"device": "gemini", "serial": "OTHER"}))
        with self.assertRaises(ValueError): self.run_installer("--device-proof", str(proof))
        self.assert_no_writes()

    def test_generic_product_accepts_same_gemini_serial_proof(self):
        self.product = "MSM8996"
        proof = self.directory / "metadata.json"
        proof.write_text(json.dumps({"device": "gemini", "serial": "PHONE",
                                     "aboot_sha256":PROFILE['aboot_sha256']}))
        self.assertEqual(self.run_installer("--device-proof", str(proof)), 0)

    def test_gemini_product_also_requires_firmware_proof(self):
        with self.assertRaises(ValueError): self.run_installer(proof=False)
        self.assert_no_writes()

    def test_different_aboot_firmware_never_flashes(self):
        self.default_proof.write_text(json.dumps({'device':'gemini','serial':'PHONE','aboot_sha256':'0'*64}))
        with self.assertRaises(ValueError): self.run_installer()
        self.assert_no_writes()


if __name__ == "__main__":
    unittest.main()
