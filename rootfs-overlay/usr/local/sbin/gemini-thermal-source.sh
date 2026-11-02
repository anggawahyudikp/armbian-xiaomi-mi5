#!/bin/sh
# Armbian's generic thermal_zone0 is the battery on Gemini, not the CPU.
set -eu
for wanted in cpu2-thermal cpu0-thermal; do
    for zone in /sys/class/thermal/thermal_zone*; do
        [ -r "$zone/type" ] && [ -r "$zone/temp" ] || continue
        [ "$(cat "$zone/type")" = "$wanted" ] || continue
        mkdir -p /etc/armbianmonitor/datasources
        ln -sfn "$zone/temp" /etc/armbianmonitor/datasources/soctemp
        exit 0
    done
done
echo 'Gemini CPU thermal sensor not found; refusing to report battery temperature as CPU' >&2
exit 1
