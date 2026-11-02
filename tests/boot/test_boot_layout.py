import gzip
import importlib.util
import pathlib
import struct
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
import boot_layout as layout


def image(span=4096, offset=0):
    return struct.pack('<2I6Q2I', 0xd503201f, 0x14000000, offset, span, 10,
                       0, 0, 0, 0x644d5241, 0).ljust(4096, b'\0')


def boot(kernel, ramdisk_address=None, dtb=None):
    if dtb is None:
        dtb = struct.pack('>2I', 0xd00dfeed, 8)
    payload = gzip.compress(kernel) + dtb
    header = struct.pack('<8s9I', b'ANDROID!', len(payload), layout.KERNEL_ADDRESS,
                         4096, ramdisk_address or layout.RAMDISK_ADDRESS, 0, 0,
                         layout.DTB_ADDRESS, 4096, 0)
    return header.ljust(4096, b'\0') + payload.ljust((len(payload)+4095)//4096*4096, b'\0') + bytes(4096)


class StockLkLayout(unittest.TestCase):
    def test_valid_wrapper_uses_effective_addresses(self):
        raw = image()
        inner, _, _, memory = layout.parse_boot_image(boot(layout.wrap_kernel(raw)))
        self.assertEqual(inner, raw)
        self.assertEqual(memory['real_kernel_address'], 0x80200000)
        self.assertEqual(memory['dtb_address'], 0x82800000)
        self.assertEqual(memory['ramdisk_address'], 0x82a00000)

    def test_bss_counts_even_when_file_is_small(self):
        with self.assertRaisesRegex(ValueError, 'stock LK permits'):
            layout.wrap_kernel(image(span=0x2600000 + 4096))

    def test_unwrapped_mainline_image_rejected(self):
        with self.assertRaisesRegex(ValueError, 'alignment wrapper'):
            layout.parse_boot_image(boot(image()))

    def test_header_cannot_move_ramdisk_out_of_the_way(self):
        with self.assertRaisesRegex(ValueError, 'stock LK layout'):
            layout.parse_boot_image(boot(layout.wrap_kernel(image()), ramdisk_address=0x84000000))

    def test_false_wrapper_span_rejected(self):
        wrapped = bytearray(layout.wrap_kernel(image()))
        struct.pack_into('<Q', wrapped, 16, 4096)
        with self.assertRaises(ValueError):
            layout.parse_boot_image(boot(bytes(wrapped)))

    def test_dtb_cannot_cross_into_ramdisk(self):
        length = 0x200000 + 8
        dtb = struct.pack('>2I', 0xd00dfeed, length).ljust(length, b'\0')
        with self.assertRaisesRegex(ValueError, 'DTB overlaps'):
            layout.parse_boot_image(boot(layout.wrap_kernel(image()), dtb=dtb))

    def test_inner_offset_must_describe_aligned_entry(self):
        with self.assertRaises(ValueError):
            layout.wrap_kernel(image(offset=0x80000))

    def test_second_stage_payload_rejected(self):
        blob = bytearray(boot(layout.wrap_kernel(image())))
        struct.pack_into('<I', blob, 24, 4096)
        with self.assertRaisesRegex(ValueError, 'second-stage'):
            layout.parse_boot_image(bytes(blob))

    @unittest.skipUnless(importlib.util.find_spec('unicorn'), 'Install Unicorn for ARM64 branch emulation')
    def test_wrapper_executes_to_aligned_kernel_and_preserves_arguments(self):
        from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM
        from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3, UC_ARM64_REG_PC
        emulator = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        emulator.mem_map(layout.KERNEL_ADDRESS, 0x200000)
        emulator.mem_write(layout.KERNEL_ADDRESS, layout.wrap_kernel(image()))
        registers = (UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3)
        values = (layout.DTB_ADDRESS, 0, 0, 0)
        for register, value in zip(registers, values):
            emulator.reg_write(register, value)
        emulator.emu_start(layout.KERNEL_ADDRESS, layout.REAL_KERNEL_ADDRESS, count=2)
        self.assertEqual(emulator.reg_read(UC_ARM64_REG_PC), layout.REAL_KERNEL_ADDRESS)
        self.assertEqual(tuple(emulator.reg_read(r) for r in registers), values)


if __name__ == '__main__':
    unittest.main()
