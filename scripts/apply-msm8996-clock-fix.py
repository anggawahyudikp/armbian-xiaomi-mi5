#!/usr/bin/env python3
"""Apply the upstream MSM8996 FD AHB register fix to a recognized source block."""
import argparse
from pathlib import Path
import re

# https://github.com/torvalds/linux/commit/7cb2d65286b817d8d7e26f454a9c374d65e87072
OLD = 0x3BA74
CORRECT = 0x3B74
RELATIVE = Path('drivers/clk/qcom/mmcc-msm8996.c')


def corrected_source(text):
    blocks = list(re.finditer(
        r'static\s+struct\s+clk_branch\s+fd_ahb_clk\s*=\s*\{.*?^\};',
        text, re.MULTILINE | re.DOTALL))
    if len(blocks) != 1:
        raise ValueError('Expected exactly one FD AHB clock definition')
    limits = re.findall(r'\.max_register\s*=\s*(0[xX][0-9a-fA-F]+)', text)
    if len(limits) != 1 or int(limits[0], 16) < CORRECT:
        raise ValueError('Unexpected MSM8996 MMCC register range')
    match = blocks[0]
    block = match.group(0)
    expressions = []
    for field in ('halt_reg', 'enable_reg'):
        expression = re.compile(r'(\.' + field + r'\s*=\s*)(0[xX][0-9a-fA-F]+)\b')
        registers = list(expression.finditer(block))
        if len(registers) != 1 or int(registers[0].group(2), 16) not in (OLD, CORRECT):
            raise ValueError('Unrecognized FD AHB ' + field + '; source left unchanged')
        expressions.append(expression)
    for expression in expressions:
        block = expression.sub(lambda register: register.group(1) + '0x3b74', block)
    return text[:match.start()] + block + text[match.end():]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kernel_source', type=Path)
    parser.add_argument('--check', action='store_true', help='Verify without changing the source')
    args = parser.parse_args()
    path = args.kernel_source / RELATIVE
    try:
        original = path.read_text()
        corrected = corrected_source(original)
        if args.check and corrected != original:
            raise ValueError('MSM8996 FD AHB clock fix is missing')
        if corrected != original:
            path.write_text(corrected)
            print('Applied upstream MSM8996 FD AHB register fix')
        else:
            print('MSM8996 FD AHB register fix verified')
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
