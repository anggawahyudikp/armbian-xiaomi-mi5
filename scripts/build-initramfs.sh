#!/usr/bin/env bash
# A small boot initramfs, or a RAM-only diagnostic environment. No rootfs overlay.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
MODE="${INITRAMFS_MODE:-production}"
case "$MODE" in production) diagnostic=0;; diagnostic) diagnostic=1;; *) exit 2;; esac
STAGING="$OUT/initramfs-$MODE"
IMAGE="${RAMDISK:-$OUT/initramfs-$MODE.cpio.gz}"
BUSYBOX="${BUSYBOX:-${ROOTFS:-$OUT/rootfs}/bin/busybox}"
CC="${CC:-aarch64-linux-gnu-gcc}"
[[ -f "$BUSYBOX" ]] || { echo "Missing static ARM64 busybox: $BUSYBOX" >&2; exit 1; }
file "$BUSYBOX" | grep -q 'ARM aarch64.*statically linked' || {
    echo "busybox must be statically linked ARM64" >&2; exit 1;
}

mkdir -p "$OUT"
rm -rf "$STAGING"
mkdir -p "$STAGING"/{bin,sbin,dev,proc,sys,root,newroot,tmp,usr/local/sbin,usr/lib/firmware}
"$CC" -static -Os -Wall -Wextra -Werror -DGEMINI_DIAGNOSTIC="$diagnostic" \
    -o "$STAGING/init" "$ROOT/initramfs/init.c"
install -m755 "$BUSYBOX" "$STAGING/bin/busybox"
for app in sh cat ls head tail dmesg mount umount mkdir sleep reboot poweroff \
    ip ifconfig route ping wget modprobe insmod rmmod lsmod blockdev \
    hexdump od vi sync uname ps top free df du find grep sed awk printf \
    readlink stat switch_root stty setsid cp mv rm date; do
    ln -s busybox "$STAGING/bin/$app"
done
ln -s usr/lib "$STAGING/lib"
install -m755 "$ROOT/initramfs/gemini-diagnostics.sh" "$STAGING/usr/local/sbin/gemini-diagnostics"
python3 - "$ROOT/initramfs/init.c" "$STAGING/usr/lib/gemini-initramfs.json" "$MODE" <<'PY'
import hashlib, json, pathlib, sys
source, output = map(pathlib.Path, sys.argv[1:3])
output.write_text(json.dumps({'mode': sys.argv[3], 'init_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}, sort_keys=True) + '\n')
PY

# Built-in ath10k may probe before switch_root. These are data, not distro binaries.
rsync -a "$ROOT/rootfs-overlay/usr/lib/firmware/" "$STAGING/usr/lib/firmware/"
python3 "$ROOT/scripts/prepare-wifi-board.py" --destination-root "$STAGING"
if [[ "$MODE" == diagnostic ]]; then
    [[ -d "$OUT/modules/lib/modules" ]] || { echo 'Build kernel modules first' >&2; exit 1; }
    krel=$(find "$OUT/modules/lib/modules" -mindepth 1 -maxdepth 1 -type d -printf '%f\n')
    [[ -n "$krel" && "$krel" != *$'\n'* ]] || { echo 'Expected one kernel module version' >&2; exit 1; }
    module_source="$OUT/modules/lib/modules/$krel"
    module_target="$STAGING/usr/lib/modules/$krel"
    mkdir -p "$module_target"
    # Copy transitive dependencies as resolved by the complete build's depmod
    # index. This subset is only for RAM diagnostics and never touches rootfs.
    for module in msm panel_jdi_fhd_r63452 hci_uart; do
        dependencies=$(modprobe --show-depends -d "$OUT/modules" -S "$krel" "$module")
        while read -r action module_file rest; do
            [[ "$action" == insmod ]] || continue
            relative="${module_file#"$module_source/"}"
            [[ "$relative" != "$module_file" ]] || { echo "Unexpected module path: $module_file" >&2; exit 1; }
            install -D -m644 "$module_file" "$module_target/$relative"
        done <<< "$dependencies"
    done
    cp "$module_source"/modules.builtin* "$module_target/"
    (cd "$module_target" && find kernel -name '*.ko*' | LC_ALL=C sort > modules.order)
    depmod -b "$STAGING" "$krel"
    # Include Gemini GPU/Bluetooth data, not the full multi-board firmware
    # package: the Android boot partition and fastboot buffer are only 64 MiB.
    if [[ -d "${ROOTFS:-$OUT/rootfs}/usr/lib/firmware" ]]; then
        (
            cd "${ROOTFS:-$OUT/rootfs}/usr/lib/firmware"
            shopt -s nullglob
            for firmware in qcom/a530* qca/*; do
                [[ -f "$firmware" ]] || continue
                install -D -m644 "$firmware" "$STAGING/usr/lib/firmware/$firmware"
            done
        )
    fi
fi

# Generate root-owned CPIO entries and console nodes without host root privileges.
python3 "$ROOT/scripts/make-initramfs.py" "$STAGING" "$IMAGE"
ls -lh "$IMAGE"
