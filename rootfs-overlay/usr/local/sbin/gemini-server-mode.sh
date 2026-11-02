#!/bin/sh
# CPU defaults shared by LCD-console and headless server operation.
set -eu
# The optional HUD can offline the big cores while blanked. Restore full CPU
# availability when switching to the server profile.
for control in /sys/devices/system/cpu/cpu*/online; do
    [ -w "$control" ] || continue
    printf '1\n' > "$control"
done
for policy in /sys/devices/system/cpu/cpufreq/policy*; do
    [ -w "$policy/scaling_governor" ] || continue
    # schedutil follows load and permits idle frequencies between requests.
    if grep -qw schedutil "$policy/scaling_available_governors"; then
        printf 'schedutil\n' > "$policy/scaling_governor"
    fi
done
