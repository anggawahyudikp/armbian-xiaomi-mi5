#!/usr/bin/env bash
# Copy local DTS overlays into the kernel tree (like Kernel-Build/overlays).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/env.sh
source "$ROOT/scripts/env.sh"

OVERLAY="$ROOT/overlays/linux"
DTS_DIR="$KERNEL_SRC/arch/arm64/boot/dts/qcom"
GEMINI="$DTS_DIR/msm8996-xiaomi-gemini.dts"
LOCAL="msm8996-xiaomi-gemini-local.dtsi"

[[ -d "$KERNEL_SRC" ]] || { echo "error: kernel source missing at $KERNEL_SRC" >&2; exit 1; }
[[ -f "$GEMINI" ]] || { echo "error: missing $GEMINI" >&2; exit 1; }

echo "==> Applying MSM8996 FD AHB clock backport"
python3 "$ROOT/scripts/apply-msm8996-clock-fix.py" "$KERNEL_SRC"

echo "==> Applying gemini DTS overlay"
install -m 644 "$OVERLAY/arch/arm64/boot/dts/qcom/$LOCAL" "$DTS_DIR/$LOCAL"

if [[ -f "$OVERLAY/drivers/video/backlight/qcom-wled.c" ]]; then
	echo "==> Applying WLED CABC-on-LK-sink skip fix"
	install -m 644 "$OVERLAY/drivers/video/backlight/qcom-wled.c" \
		"$KERNEL_SRC/drivers/video/backlight/qcom-wled.c"
fi

if [[ -f "$OVERLAY/drivers/gpu/drm/panel/panel-jdi-fhd-r63452.c" ]]; then
	echo "==> Applying JDI R63452 panel (DCS sleep, no GPIO reset on DPMS)"
	install -m 644 "$OVERLAY/drivers/gpu/drm/panel/panel-jdi-fhd-r63452.c" \
		"$KERNEL_SRC/drivers/gpu/drm/panel/panel-jdi-fhd-r63452.c"
fi

if [[ -f "$OVERLAY/drivers/gpu/drm/msm/dsi/dsi_host.c" ]]; then
	echo "==> Applying DSI pclk RCG retry after PLL enable"
	install -m 644 "$OVERLAY/drivers/gpu/drm/msm/dsi/dsi_host.c" \
		"$KERNEL_SRC/drivers/gpu/drm/msm/dsi/dsi_host.c"
fi

if [[ -f "$OVERLAY/drivers/gpu/drm/msm/dsi/dsi_manager.c" ]]; then
	echo "==> Applying DSI analog-keep (skip PHY power-down on CRTC off)"
	install -m 644 "$OVERLAY/drivers/gpu/drm/msm/dsi/dsi_manager.c" \
		"$KERNEL_SRC/drivers/gpu/drm/msm/dsi/dsi_manager.c"
fi

echo "==> Applying PMI8994 FG / SMBCHG drivers (msm8996-mainline)"
install -m 644 "$OVERLAY/drivers/power/supply/qcom_fg.c" \
	"$KERNEL_SRC/drivers/power/supply/qcom_fg.c"
install -m 644 "$OVERLAY/drivers/power/supply/qcom-smbchg.c" \
	"$KERNEL_SRC/drivers/power/supply/qcom-smbchg.c"
install -m 644 "$OVERLAY/drivers/power/supply/qcom-smbchg.h" \
	"$KERNEL_SRC/drivers/power/supply/qcom-smbchg.h"
install -m 644 "$OVERLAY/drivers/soc/qcom/pmic-sec-write.c" \
	"$KERNEL_SRC/drivers/soc/qcom/pmic-sec-write.c"
install -d "$KERNEL_SRC/include/soc/qcom"
install -m 644 "$OVERLAY/include/soc/qcom/pmic-sec-write.h" \
	"$KERNEL_SRC/include/soc/qcom/pmic-sec-write.h"

python3 - "$KERNEL_SRC" <<'PY'
import pathlib, sys
src = pathlib.Path(sys.argv[1])

def once(path, needle, insert_after, block):
    p = pathlib.Path(path)
    t = p.read_text()
    if needle in t:
        return
    i = t.find(insert_after)
    if i < 0:
        raise SystemExit(f"anchor missing in {path}: {insert_after!r}")
    i += len(insert_after)
    p.write_text(t[:i] + block + t[i:])

# The MSM framebuffer is a kernel virtual mapping of a GEM buffer.
once(src / "drivers/gpu/drm/msm/msm_fbdev.c",
     "fbi->flags |= FBINFO_VIRTFB;",
     "\tdrm_fb_helper_fill_info(fbi, helper, sizes);\n",
     "\tfbi->flags |= FBINFO_VIRTFB;\n")

once(src / "drivers/usb/gadget/legacy/serial.c",
     ".MaxPower\t= CONFIG_USB_GADGET_VBUS_DRAW",
     "\t.bmAttributes\t= USB_CONFIG_ATT_SELFPOWER,\n",
     "\t.MaxPower\t= CONFIG_USB_GADGET_VBUS_DRAW,\n")

# Gadget configuration/suspend limits apply to a standard downstream port.
# A charger port has no host configuration; SMBCHG owns its AICL negotiation.
# In particular, unbinding legacy ACM must not suspend a dedicated charger.
once(src / "drivers/usb/dwc3/core.c",
     "Leave charger-port current negotiation to the power supply",
     "\tval.intval = 1000 * (dwc->current_limit);\n",
     """
	/* Leave charger-port current negotiation to the power supply. */
	ret = power_supply_get_property(dwc->usb_psy,
				       POWER_SUPPLY_PROP_USB_TYPE, &val);
	if (!ret && (val.intval == POWER_SUPPLY_USB_TYPE_DCP ||
		     val.intval == POWER_SUPPLY_USB_TYPE_CDP))
		return;

	val.intval = 1000 * dwc->current_limit;
""")
once(src / "Documentation/devicetree/bindings/usb/snps,dwc3.yaml",
     "  usb-psy-name:",
     "properties:\n",
     """
  usb-psy-name:
    $ref: /schemas/types.yaml#/definitions/string
    description:
      Name of the USB power supply which receives the gadget's negotiated
      VBUS current limit. The DWC3 driver updates input-current-limit on it.

""")

once(src / "drivers/power/supply/Kconfig",
     "config CHARGER_QCOM_SMBCHG",
     "\t  'pm8941_charger'.\n",
     """
config CHARGER_QCOM_SMBCHG
	tristate "Qualcomm Switch-Mode Battery Charger (PMI8994)"
	depends on MFD_SPMI_PMIC || COMPILE_TEST
	depends on OF
	depends on EXTCON
	depends on REGULATOR
	select QCOM_PMIC_SEC_WRITE
	help
	  SMBCHG on PMI8994 / PMI8996. Xiaomi Mi 5 uses this for USB charging
	  status. Pair with BATTERY_QCOM_FG for current_now / voltage_now.
""")
once(src / "drivers/power/supply/Kconfig",
     "config BATTERY_QCOM_FG",
     "\t  power supply information.\n",
     """
config BATTERY_QCOM_FG
	tristate "Qualcomm PMIC fuel gauge (PMI8994)"
	depends on MFD_SPMI_PMIC || COMPILE_TEST
	help
	  PMI8994/PMI8998 fuel gauge. Registers qcom-battery with capacity,
	  voltage_now and current_now (whole-device power ≈ |I|×V).
""")
once(src / "drivers/power/supply/Makefile",
     "CHARGER_QCOM_SMBCHG",
     "obj-$(CONFIG_CHARGER_QCOM_SMBB)\t+= qcom_smbb.o\n",
     "obj-$(CONFIG_CHARGER_QCOM_SMBCHG)\t+= qcom-smbchg.o\n")
once(src / "drivers/power/supply/Makefile",
     "BATTERY_QCOM_FG",
     "obj-$(CONFIG_BATTERY_UG3105)\t+= ug3105_battery.o\n",
     "obj-$(CONFIG_BATTERY_QCOM_FG)\t+= qcom_fg.o\n")
once(src / "drivers/soc/qcom/Kconfig",
     "config QCOM_PMIC_SEC_WRITE",
     "\t  PBS trigger event to the PBS RAM.\n",
     """
config QCOM_PMIC_SEC_WRITE
	bool
	help
	  Secure PMIC register write helpers used by SMBCHG.
""")
once(src / "drivers/soc/qcom/Makefile",
     "pmic-sec-write.o",
     "obj-$(CONFIG_QCOM_PBS) +=	qcom-pbs.o\n",
     "obj-$(CONFIG_QCOM_PMIC_SEC_WRITE) += pmic-sec-write.o\n")
print("    kconfig/makefile patched")
PY

# msm8996-mainline: units exist with board-id 31 and 32.
if grep -q 'qcom,board-id = <31 0>;' "$GEMINI"; then
	sed -i 's/qcom,board-id = <31 0>;/qcom,board-id = <31 0>, <32 0>;/' "$GEMINI"
fi

if ! grep -q "$LOCAL" "$GEMINI"; then
	printf '\n#include "%s"\n' "$LOCAL" >> "$GEMINI"
fi

echo "    board-id: $(grep 'qcom,board-id' "$GEMINI")"
echo "    included: $LOCAL"
