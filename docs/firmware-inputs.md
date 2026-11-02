# Local firmware inputs

The public repository contains source code, build configuration and sanitized
measurement summaries. Device firmware, phone backups and personalized images
are not included. The GPL license for project code does not relicense firmware.

Before building, restore the needed firmware files from your own compatible
Mi 5 installation or another source whose terms permit your intended use.
Keep the files in the ignored local directory below:

| Local directory | Inputs |
| --- | --- |
| rootfs-overlay/usr/lib/firmware/ath10k/QCA6174/hw3.0/ | QCA6174 firmware API files, such as firmware-4.bin and firmware-6.bin |
| rootfs-overlay/usr/lib/firmware/qcom/msm8996/gemini/ | Adreno A530 zap files, including a530_zap.mbn, .mdt and matching .b00/.b01/.b02 segments |
| rootfs-overlay/usr/lib/firmware/ | regulatory.db and its signature from your distribution's wireless regulatory database package |
| firmware/gemini/ath10k/QCA6174/hw3.0/ | The verified Mi 5 board-pci-0000:01:00.0.bin local build input |

Use the complete matching file sets from a compatible installation; do not mix
segments from different firmware builds. The device-specific board file is
prepared and checksum-validated by the [Wi-Fi board-data tool](wifi-board-data.md).
The old generic board.bin is not accepted as that input.

The build copies local firmware into the initramfs and rootfs and records
input identities. Missing firmware can prevent Wi-Fi or display operation.
Do not publish original modem or persist partitions to solve a missing input.

The board utilities gemini-status, gemini-fb-ui and reboot-bootloader are built
from initramfs/ C sources by scripts/build-utilities.sh; precompiled copies are
not required in the source tree.

Host unit tests use synthetic data and mocks. One test for an optional legacy
board.bin fixture is explicitly skipped when that private fixture is absent;
the mandatory invalid/corrupt board-data rejection tests still run. CI does not
build a firmware-equipped image or claim hardware coverage.
