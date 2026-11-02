#!/bin/sh
# Read-only summary for the RAM-only diagnostic image. Never mount userdata.
echo '=== Kernel ==='
uname -a
cat /proc/cmdline
echo '=== Memory and root mounts ==='
head /proc/meminfo
cat /proc/mounts
echo '=== Partitions (read-only flag) ==='
for node in /sys/class/block/sd*; do
    [ -e "$node/ro" ] || continue
    printf '%s ro=' "${node##*/}"
    cat "$node/ro"
    cat "$node/uevent"
done
echo '=== Network, USB and framebuffer ==='
ls /sys/class/net /sys/class/udc /sys/class/drm /sys/class/graphics
echo '=== Battery ==='
for node in /sys/class/power_supply/*; do
    [ -f "$node/uevent" ] && cat "$node/uevent"
done
echo '=== Recent kernel log ==='
dmesg | tail -100
