# Kernel test fixture

The DWC3 callback excerpt comes from drivers/usb/dwc3/core.c at Linux commit
028ef9c96e96197026887c0f092424679298aae8. Its GPL-2.0 license is retained.
The test applies the actual production patch operation extracted from
scripts/apply-overlays.sh before compiling the callback against mocked power
supplies. No local kernel checkout, network download or phone is required.

Source: https://github.com/torvalds/linux/blob/028ef9c96e96197026887c0f092424679298aae8/drivers/usb/dwc3/core.c
