#!/bin/sh
set -eu
modprobe panel_jdi_fhd_r63452
modprobe msm
for n in $(seq 1 100); do
    [ ! -e /sys/class/graphics/fb0/blank ] || break
    sleep 0.2
done
[ -e /sys/class/graphics/fb0/blank ]
# A readable font for the 1080x1920 LCD. Keep the distribution getty/login.
font=/usr/share/consolefonts/Lat15-TerminusBold32x16.psf.gz
if [ -f "$font" ]; then
    setfont -C /dev/tty1 "$font" || true
fi
chvt 1
# Production console is quiet; diagnostics retain the verbose boot command line.
printf 'N\n' > /sys/module/printk/parameters/ignore_loglevel
