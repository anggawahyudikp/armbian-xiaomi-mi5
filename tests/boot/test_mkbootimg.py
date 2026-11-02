"""Exercise the real legacy packager and dependency-selection failure paths."""
import gzip
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import boot_layout


class BootPackager(unittest.TestCase):
    def test_standalone_tool_packs_the_stock_lk_memory_layout(self):
        raw = struct.pack('<2I6Q2I', 0xd503201f, 0x14000000, 0, 4096, 10,
                          0, 0, 0, 0x644d5241, 0).ljust(4096, b'\0')
        dtb = struct.pack('>2I', 0xd00dfeed, 8)
        ramdisk = gzip.compress(b'fixture ramdisk', mtime=0)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            kernel = tmp / 'kernel'
            kernel.write_bytes(gzip.compress(boot_layout.wrap_kernel(raw), mtime=0) + dtb)
            (tmp / 'ramdisk').write_bytes(ramdisk)
            profile = boot_layout.PROFILE
            subprocess.run([sys.executable, str(ROOT / 'scripts/vendor/mkbootimg.py'),
                            '--header_version', '0', '--kernel', str(kernel),
                            '--ramdisk', str(tmp / 'ramdisk'), '--pagesize', '4096',
                            '--base', hex(profile['ddr_base']),
                            '--kernel_offset', hex(profile['kernel_address'] - profile['ddr_base']),
                            '--ramdisk_offset', hex(profile['ramdisk_address'] - profile['ddr_base']),
                            '--tags_offset', hex(profile['dtb_address'] - profile['ddr_base']),
                            '-o', str(tmp / 'boot.img')], check=True, timeout=15)
            inner, packed_dtb, packed_ramdisk, memory = boot_layout.parse_boot_image((tmp / 'boot.img').read_bytes())
            self.assertEqual(inner, raw)
            self.assertEqual(packed_ramdisk, ramdisk)
            self.assertEqual(packed_dtb, dtb)
            self.assertEqual(memory['real_kernel_address'], boot_layout.REAL_KERNEL_ADDRESS)

    def run_preflight(self, override):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            output = tmp / 'output'
            output.mkdir()
            (output / 'Image.gz').write_bytes(b'preflight fixture')
            (output / 'msm8996-xiaomi-gemini.dtb').write_bytes(b'preflight fixture')
            busybox = tmp / 'busybox'
            busybox.write_bytes(b'not an ARM64 static executable')
            tools = tmp / 'bin'
            tools.mkdir()
            broken = tools / 'mkbootimg'
            broken.write_text('#!/bin/sh\necho BROKEN_HOST_PACKAGER_CALLED >&2\nexit 91\n')
            broken.chmod(0o755)
            env = {**os.environ, 'OUT': str(output), 'BUSYBOX': str(busybox),
                   'PATH': str(tools) + os.pathsep + os.environ['PATH']}
            env.pop('MKBOOTIMG', None)
            if override:
                env['MKBOOTIMG'] = str(broken)
            return subprocess.run(['bash', str(ROOT / 'scripts/build-bootimg.sh')],
                                  env=env, capture_output=True, text=True, timeout=20)

    def test_default_does_not_use_a_broken_host_packager(self):
        result = self.run_preflight(override=False)
        self.assertNotEqual(result.returncode, 0)  # Deliberately invalid BusyBox.
        self.assertIn('busybox must be statically linked ARM64', result.stderr)
        self.assertNotIn('BROKEN_HOST_PACKAGER_CALLED', result.stderr)
        self.assertIn(str(ROOT / 'scripts/vendor/mkbootimg.py'), result.stdout)

    def test_broken_explicit_override_fails_before_initramfs_work(self):
        result = self.run_preflight(override=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BROKEN_HOST_PACKAGER_CALLED', result.stderr)
        self.assertNotIn('busybox must be statically linked ARM64', result.stderr)


if __name__ == '__main__':
    unittest.main()
