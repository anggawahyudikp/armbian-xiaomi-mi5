#!/sbin/sh
# Both payloads are staged and verified in RAM before userdata is formatted.
OUTFD=${2:-1}
ZIPFILE=$3
WORK=/tmp/gemini-install
TARGET=/mnt/gemini-install
ui_print() { printf 'ui_print %s\nui_print\n' "$1" >&$OUTFD; }
abort() { ui_print "ERROR: $1"; exit 1; }
cleanup() { umount "$TARGET" 2>/dev/null || true; rm -rf "$WORK"; }
trap cleanup EXIT

DEVICE=$(getprop ro.product.device)
[ -n "$DEVICE" ] || DEVICE=$(getprop ro.build.product)
case "$DEVICE" in gemini|omni_gemini) ;; *) abort "This package is only for gemini ($DEVICE detected)";; esac
BOOT_DEV=""
USERDATA_DEV=""
ABOOT_DEV=""
for BASE in /dev/block/bootdevice/by-name /dev/block/by-name /dev/block/platform/soc/624000.ufshc/by-name; do
    [ -b "$BASE/boot" ] && [ -b "$BASE/userdata" ] && [ -b "$BASE/aboot" ] || continue
    BOOT_DEV=$(readlink -f "$BASE/boot")
    USERDATA_DEV=$(readlink -f "$BASE/userdata")
    ABOOT_DEV=$(readlink -f "$BASE/aboot")
    break
done
[ -n "$BOOT_DEV" ] && [ -n "$USERDATA_DEV" ] || abort 'Boot/userdata partitions not found'
[ "$BOOT_DEV" != "$USERDATA_DEV" ] || abort 'Partition identity check failed'

ui_print 'Armbian community port for Xiaomi Mi 5'
ui_print 'Installation ERASES ALL Android userdata.'
ui_print 'Checking and staging both payloads in RAM before formatting...'
mkdir -p "$WORK" "$TARGET" || abort 'Cannot create staging directories'
for FILE in boot.img rootfs.tar.gz SHA256SUMS rootfs-min-bytes bootloader-sha256; do
    unzip -p "$ZIPFILE" "$FILE" > "$WORK/$FILE" || abort "Cannot extract $FILE"
    [ -s "$WORK/$FILE" ] || abort "Empty payload: $FILE"
done
(cd "$WORK" && sha256sum -c SHA256SUMS) || abort 'Payload checksum mismatch'
EXPECTED_ABOOT=$(cat "$WORK/bootloader-sha256")
[ "${#EXPECTED_ABOOT}" -eq 64 ] || abort 'Invalid aboot profile digest'
ACTUAL_ABOOT=$(sha256sum "$ABOOT_DEV") || abort 'Cannot identify aboot firmware'
[ "${ACTUAL_ABOOT%% *}" = "$EXPECTED_ABOOT" ] || abort 'Unsupported aboot firmware/load-address layout'
gzip -t "$WORK/rootfs.tar.gz" || abort 'Rootfs gzip is corrupt'
tar -tzf "$WORK/rootfs.tar.gz" > /dev/null || abort 'Rootfs tar is corrupt'
BOOT_SIZE=$(wc -c < "$WORK/boot.img")
BOOT_CAPACITY=$(blockdev --getsize64 "$BOOT_DEV") || abort 'Cannot read boot partition size'
DATA_CAPACITY=$(blockdev --getsize64 "$USERDATA_DEV") || abort 'Cannot read userdata partition size'
MIN_BYTES=$(cat "$WORK/rootfs-min-bytes")
case "$MIN_BYTES" in ''|*[!0-9]*) abort 'Invalid minimum rootfs size';; esac
[ "$BOOT_SIZE" -le "$BOOT_CAPACITY" ] || abort 'Boot image is larger than boot partition'
[ "$MIN_BYTES" -le "$DATA_CAPACITY" ] || abort 'Rootfs does not fit userdata'

# Unmount children before their parent. Every failure aborts before formatting.
awk -v target="$USERDATA_DEV" '$1==target || $2=="/data" || $2 ~ /^\/data\// || $2=="/sdcard" || $2 ~ /^\/sdcard\// { print $2 }' /proc/mounts |
    sort -r > "$WORK/mounts"
while IFS= read -r POINT; do
    umount "$POINT" || abort "Cannot unmount $POINT"
done < "$WORK/mounts"
while read -r SOURCE POINT REST; do
    [ "$(readlink -f "$SOURCE" 2>/dev/null)" != "$USERDATA_DEV" ] || abort 'userdata is still mounted'
done < /proc/mounts

ui_print 'Formatting userdata as ext4...'
mke2fs -t ext4 -F -L rootfs -O ^metadata_csum,^64bit "$USERDATA_DEV" || abort 'Format failed'
mount -t ext4 -o rw,noatime "$USERDATA_DEV" "$TARGET" || abort 'Cannot mount new rootfs'
tar -xzpf "$WORK/rootfs.tar.gz" -C "$TARGET" || abort 'Rootfs extraction failed'
[ "$(cat "$TARGET/etc/gemini-rootfs")" = gemini-rootfs-v1 ] || abort 'Wrong rootfs marker'
[ -f "$TARGET/etc/armbian-release" ] || abort 'Missing Armbian metadata'
sync
umount "$TARGET" || abort 'Cannot cleanly unmount new rootfs'
ui_print 'Writing boot image...'
dd if="$WORK/boot.img" of="$BOOT_DEV" bs=4096 || abort 'Boot write failed'
sync
ui_print 'Installation finished. Reboot and complete Armbian first-login setup.'
exit 0
