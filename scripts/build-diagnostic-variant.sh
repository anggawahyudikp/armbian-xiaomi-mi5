#!/usr/bin/env bash
# Prepare a conservative USB bring-up image; never reboot or flash a device.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
[[ -f "$OUT/$DTB_NAME" && -f "$OUT/Image.gz" ]] || { echo 'Build the base kernel/DTB first' >&2; exit 1; }
VARIANT_DTB="msm8996-xiaomi-gemini-usb-debug.dtb"
cp "$OUT/$DTB_NAME" "$OUT/$VARIANT_DTB"

# Isolate peripheral probe/clock/secondary-CPU failures. This DTB is only for
# diagnostics: production hardware support must still be brought up and tested.
while read -r symbol fallback; do
    path=$(fdtget -t s "$OUT/$VARIANT_DTB" /__symbols__ "$symbol" 2>/dev/null || true)
    path="${path:-$fallback}"
    # Normal kernel DTBs need not contain __symbols__. These fallback paths
    # correspond to the pinned Gemini v7.0 tree; fail if that layout changes.
    fdtget -t s "$OUT/$VARIANT_DTB" "$path" compatible >/dev/null
    fdtput -t s "$OUT/$VARIANT_DTB" "$path" status disabled
    echo "USB debug: disabled $symbol ($path)"
done <<'NODES'
pcie0 /soc@0/bus@0/pcie@600000
mdss /soc@0/display-subsystem@900000
gpu /soc@0/gpu@b00000
ufshc /soc@0/ufshc@624000
pmi8994_smbchg /soc@0/spmi@400f000/pmic@2/charger@1000
pmi8994_fg /soc@0/spmi@400f000/pmic@2/fuel-gauge@4000
NODES
# The minimal variant disables the charger. Avoid a permanent DWC3 probe
# deferral while waiting for a power supply which this variant cannot create.
fdtput -d "$OUT/$VARIANT_DTB" /soc@0/usb@6af8800/usb@6a00000 usb-psy-name
CMDLINE='console=ttyGS0,115200 console=tty0 ignore_loglevel loglevel=8 initcall_debug maxcpus=1 cpuidle.off=1 clk_ignore_unused pd_ignore_unused no_console_suspend'
export CMDLINE
DTB_NAME="$VARIANT_DTB" INITRAMFS_MODE=diagnostic \
    BOOTIMG="$OUT/boot-diagnostic-usb-debug.img" "$ROOT/scripts/build-bootimg.sh"
python3 "$ROOT/scripts/inspect-bootimg.py" "$OUT/boot-diagnostic-usb-debug.img" \
    --mode diagnostic --report "$OUT/usb-debug-verification.json"
echo 'Prepared only. Repeat hardware testing when a physical reset is available.'
