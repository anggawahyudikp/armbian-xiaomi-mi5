#!/usr/bin/env python3
"""Emulate the known installed aboot's header-address function, entirely offline.

Requires pyelftools and Unicorn. The firmware binary stays in ignored out/.
No device tools or firmware writes are used by this program.
"""
import argparse
import hashlib
import json
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'scripts'))
from boot_layout import PROFILE
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('aboot', type=pathlib.Path)
parser.add_argument('--report', type=pathlib.Path, required=True)
args = parser.parse_args()
digest = hashlib.sha256(args.aboot.read_bytes()).hexdigest()
if digest != PROFILE['aboot_sha256']:
    raise SystemExit('Unknown aboot: function offsets are valid only for the audited firmware hash')
with args.aboot.open('rb') as stream:
    elf = ELFFile(stream)
    segment = next(s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD')
    contents, base = segment.data(), segment['p_vaddr']
results = []
for is64 in (False, True):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.mem_map(base, 0x200000)
    machine.mem_write(base, contents)
    # This cached DDR base is normally set by the SMEM RAM table parser.
    machine.mem_write(0x92bcaab8, struct.pack('<Q', PROFILE['ddr_base']))
    machine.mem_map(0x90000000, 0x1000)
    machine.mem_map(0x91000000, 0x10000)
    machine.mem_map(0x93000000, 0x1000)
    header = bytearray(4096)
    # Deliberately use the old build's requested addresses to test overrides.
    for offset, value in ((12, 0x80008000), (20, 0x84000000), (32, 0x80000100)):
        struct.pack_into('<I', header, offset, value)
    machine.mem_write(0x90000000, bytes(header))
    machine.reg_write(UC_ARM_REG_R0, 0x90000000)
    machine.reg_write(UC_ARM_REG_R1, int(is64))
    machine.reg_write(UC_ARM_REG_SP, 0x9100fff0)
    machine.reg_write(UC_ARM_REG_LR, 0x93000000)
    machine.emu_start(0x92a3957c, 0x93000000, count=300)
    assert machine.reg_read(UC_ARM_REG_PC) == 0x93000000, 'Function did not return'
    actual = {key: struct.unpack('<I', machine.mem_read(0x90000000 + offset, 4))[0]
              for key, offset in (('kernel_address', 12), ('ramdisk_address', 20), ('dtb_address', 32))}
    expected = {key: PROFILE[key] for key in actual}
    if not is64:
        expected['kernel_address'] = PROFILE['ddr_base'] + 0x8000
    assert actual == expected, (actual, expected)
    results.append({'arm64': is64, **actual})
report = {'passed': True, 'executed_on_device': False, 'aboot_sha256': digest,
          'emulated_function': '0x92a3957c', 'ddr_base': PROFILE['ddr_base'], 'results': results}
args.report.write_text(json.dumps(report, indent=2) + '\n')
print('Installed aboot emulation matches firmware-specific address profile for ARM32/ARM64')
