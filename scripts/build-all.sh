#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
python3 "$ROOT/scripts/prepare-wifi-board.py" --check

echo "=== [1/5] Setting up Linux Mainline Kernel ==="
"$ROOT/scripts/setup-kernel.sh"

bash "$ROOT/tests/boot/run.sh"

echo "=== [2/5] Cross-Compiling Kernel & Device Tree ==="
"$ROOT/scripts/build-kernel.sh"
python3 -m unittest discover -s "$ROOT/tests/server" -p 'test_*.py'

echo "=== [3/5] Building Gemini utilities and Armbian userspace ==="
"$ROOT/scripts/build-utilities.sh"
"$ROOT/scripts/build-rootfs.sh"

echo "=== [4/5] Building production and RAM-only diagnostic boot images ==="
"$ROOT/scripts/build-bootimg.sh"
INITRAMFS_MODE=diagnostic "$ROOT/scripts/build-bootimg.sh"
python3 "$ROOT/scripts/inspect-bootimg.py" "$OUT/boot.img" --mode production \
    --require-server-config --report "$OUT/boot-validation.json"
python3 "$ROOT/scripts/inspect-bootimg.py" "$OUT/boot-diagnostic.img" --mode diagnostic \
    --require-server-config --report "$OUT/boot-diagnostic-validation.json"

"$ROOT/scripts/build-diagnostic-variant.sh"
python3 "$ROOT/scripts/inspect-bootimg.py" "$OUT/boot-diagnostic-usb-debug.img" --mode diagnostic \
    --require-server-config --report "$OUT/usb-debug-verification.json"
python3 "$ROOT/scripts/verify-rootfs-image.py" "$OUT"

echo "=== [5/5] Generating Custom ROM Release Packages ==="
"$ROOT/scripts/build-twrp-zip.sh"
"$ROOT/scripts/build-fastboot-package.sh"
python3 "$ROOT/tests/boot/verify-release.py" "$OUT"

python3 "$ROOT/scripts/record-build.py" "$OUT" --kernel-output "$KBUILD_OUTPUT"
"$ROOT/scripts/publish-release.sh" --prepare

echo "=== ALL BUILDS COMPLETED SUCCESSFULLY! ==="
ls -lh "$OUT"
