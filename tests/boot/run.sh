#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TEMP=$(mktemp -d)
trap 'rm -rf "$TEMP"' EXIT
for mode in 0 1; do
    gcc -O2 -Wall -Wextra -Werror -DGEMINI_DIAGNOSTIC="$mode" \
        "$ROOT/tests/boot/test-init-safety.c" -o "$TEMP/test-init"
    "$TEMP/test-init"
done
python3 "$ROOT/tests/boot/test_fastboot_install.py"
python3 "$ROOT/tests/boot/test_boot_layout.py"
python3 "$ROOT/tests/boot/test_mkbootimg.py"
python3 "$ROOT/tests/boot/test_usb_identity.py"
python3 "$ROOT/tests/boot/test_wifi_board.py"
python3 "$ROOT/tests/boot/test_clock_fix.py"
python3 "$ROOT/tests/boot/test_kernel_source_identity.py"
