#!/usr/bin/env bash
# Pack Android boot.img v0 for Xiaomi Mi 5 (gemini / MSM8996).
# The installed LK forces load addresses regardless of the Android header.
# boot_layout.py wraps the mainline Image for alignment and checks its complete
# in-memory size against the fixed DTB/ramdisk layout verified from aboot.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/env.sh
source "$ROOT/scripts/env.sh"

KERNEL="$OUT/Image.gz"
DTB="$OUT/$DTB_NAME"
INITRAMFS_MODE="${INITRAMFS_MODE:-production}"
export INITRAMFS_MODE
suffix=""
[[ "$INITRAMFS_MODE" == diagnostic ]] && suffix="-diagnostic"
BOOTIMG="${BOOTIMG:-$OUT/boot$suffix.img}"
export RAMDISK="${RAMDISK:-$OUT/initramfs-$INITRAMFS_MODE.cpio.gz}"
read -r KERNEL_OFFSET RAMDISK_OFFSET TAGS_OFFSET < <(
    PYTHONPATH="$ROOT/scripts" python3 -c 'from boot_layout import PROFILE; print(*(hex(PROFILE[k]-PROFILE["ddr_base"]) for k in ("kernel_address","ramdisk_address","dtb_address")))'
)
SECOND_OFFSET=0x04f00000

# Last console= wins as /dev/console. tty0 last → fbcon is the panel console
# (ginkgo same trick). ttyGS0 still gets a printk copy on USB ACM.
# Do not use earlycon at 0x7570000 (BT UART). GDM stays masked.
console_logging='loglevel=4 consoleblank=0'
[[ "$INITRAMFS_MODE" != diagnostic ]] || console_logging='ignore_loglevel loglevel=8'
CMDLINE="${CMDLINE:-console=ttyGS0,115200 console=tty0 $console_logging root=/dev/disk/by-partlabel/userdata rootwait rw maxcpus=4 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory swapaccount=1 net.ifnames=0 max_loop=128}"

[[ -f "$KERNEL" ]] || { echo "missing $KERNEL — run scripts/build-kernel.sh first" >&2; exit 1; }
[[ -f "$DTB" ]] || { echo "missing $DTB — run scripts/build-kernel.sh first" >&2; exit 1; }

# Use the pinned standalone tool instead of host packages with missing GKI
# Python modules. An explicit override still gets the same early preflight.
MKBOOTIMG="${MKBOOTIMG:-$ROOT/scripts/vendor/mkbootimg.py}"
command -v "$MKBOOTIMG" >/dev/null || { echo "Boot packager is not executable: $MKBOOTIMG" >&2; exit 1; }
"$MKBOOTIMG" --help >/dev/null || {
    echo 'mkbootimg cannot start; repair its Python dependencies or set MKBOOTIMG to a working executable.' >&2
    exit 1
}
echo "Boot packager: $MKBOOTIMG"

"$ROOT/scripts/build-initramfs.sh"
[[ -f "$RAMDISK" ]] || { echo "missing $RAMDISK" >&2; exit 1; }

# LK places the compressed ramdisk at the header address. Do not overwrite
# reserved firmware memory (the first reservation is normally 0x85800000).
PYTHONPATH="$ROOT/scripts" python3 - "$DTB" "$RAMDISK" <<'PY'
import os, subprocess, sys
from boot_layout import RAMDISK_ADDRESS
dtb, ramdisk = sys.argv[1:]
start, end = RAMDISK_ADDRESS, RAMDISK_ADDRESS + os.path.getsize(ramdisk)
nodes = subprocess.check_output(['fdtget', '-l', dtb, '/reserved-memory'], text=True).splitlines()
for node in nodes:
    result = subprocess.run(['fdtget', '-t', 'x', dtb, '/reserved-memory/' + node, 'reg'],
                            capture_output=True, text=True)
    if result.returncode:
        continue  # dynamically allocated reserved-memory node
    cells = [int(word, 16) for word in result.stdout.split()]
    for offset in range(0, len(cells), 4):
        address = (cells[offset] << 32) | cells[offset + 1]
        size = (cells[offset + 2] << 32) | cells[offset + 3]
        if start < address + size and address < end:
            raise SystemExit(f'Ramdisk 0x{start:x}-0x{end:x} overlaps reserved-memory/{node}')
print(f'Ramdisk memory range 0x{start:x}-0x{end:x} does not overlap firmware reservations')
PY

mkdir -p "$OUT"
PYTHONPATH="$ROOT/scripts" python3 - "$KERNEL" "$DTB" "$OUT/Image.gz-dtb" <<'PY'
import gzip, pathlib, sys
from boot_layout import wrap_kernel, unwrap_kernel
kernel, dtb, output = map(pathlib.Path, sys.argv[1:])
wrapped = wrap_kernel(gzip.decompress(kernel.read_bytes()))
_, layout = unwrap_kernel(wrapped)
output.write_bytes(gzip.compress(wrapped, mtime=0) + dtb.read_bytes())
print('Stock LK memory layout:', layout)
PY

echo "==> Packing $(basename "$BOOTIMG")"
"$MKBOOTIMG" \
	--header_version 0 \
	--kernel "$OUT/Image.gz-dtb" \
	--ramdisk "$RAMDISK" \
	--cmdline "$CMDLINE" \
	--pagesize 4096 \
	--base 0x80000000 \
	--kernel_offset "$KERNEL_OFFSET" \
	--ramdisk_offset "$RAMDISK_OFFSET" \
	--second_offset "$SECOND_OFFSET" \
	--tags_offset "$TAGS_OFFSET" \
	-o "$BOOTIMG"

PYTHONPATH="$ROOT/scripts" python3 - "$BOOTIMG" <<'PY'
import pathlib, sys
from boot_layout import parse_boot_image
p = sys.argv[1]
_, _, _, layout = parse_boot_image(pathlib.Path(p).read_bytes())
print('Stock LK header/wrapper/memory checks passed:', layout)
PY

ls -lh "$BOOTIMG"
if [[ "$INITRAMFS_MODE" == diagnostic ]]; then
    echo "RAM-only hardware test: fastboot boot $BOOTIMG"
else
    echo "Production image: requires a validated Gemini rootfs on userdata."
    echo "For an Android-preserving hardware test, build INITRAMFS_MODE=diagnostic."
fi
