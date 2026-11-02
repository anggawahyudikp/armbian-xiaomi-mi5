#!/usr/bin/env bash
# Build board-specific programs; distribution binaries always come from APT.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
CC="${CC:-aarch64-linux-gnu-gcc}"
DEST="$OUT/utilities/usr/local/sbin"
mkdir -p "$DEST"
for program in reboot-bootloader gemini-fb-ui; do
    "$CC" -static -Os -Wall -Wextra -o "$DEST/$program" "$ROOT/initramfs/$program.c"
done
"$CC" -static -O2 -Wall -Wextra -pthread -o "$DEST/gemini-status" \
    "$ROOT/initramfs/gemini-status.c" "$ROOT/initramfs/gemini-status-gpu-stub.c" -lm
ln -sfn reboot-bootloader "$DEST/reboot-fastboot"
file "$DEST/gemini-status"
