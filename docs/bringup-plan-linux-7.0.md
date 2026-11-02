# Historical Linux 7.0 bring-up plan

Recorded August 2026. This describes the earlier Ubuntu/umeko installation,
not the current Armbian installer. Current stock-LK memory rules are documented
in the [October bootloader audit](bootloader-memory-2026-10-29.md).

Baseline: Ubuntu 20.04 with `6.1.14-umeko-rv0` on userdata. Target: torvalds v7.0
and upstream `msm8996-xiaomi-gemini.dts`. Daily testing replaced boot only,
retaining the existing Ubuntu rootfs and TWRP recovery.

Principles:

1. Preserve the only working 6.1 boot; test in RAM or back up before writing.
2. Establish UFS userdata, USB serial and readable dmesg first.
3. Add display, touch and Wi-Fi in stages against a real live dump.
4. Select only missing, device-relevant msm8996-mainline staging patches.

| Stage | Work and historical result |
|---|---|
| P0 | TWRP partition/config/firmware/cmdline inventory; Ubuntu live dump; Synaptics S3330, QCA6174 PCIe and 1080×1920 DRM confirmed |
| P1 | Build Image.gz, Gemini DTB and Android boot image; check UFS, serial and panel config; back up boot |
| P2 | 27 August: RAM boot reached Ubuntu 20.04.6 as `7.0.0-umeko-rv0-dirty`; g_serial autologin; partition 6.1 unchanged |
| P3 | MSM DRM/fb0 appeared; MDP required the GPU component; generic APQ8096 zap still failed with −5 |
| P4 | RMI4 I2C `2-0020` Synaptics S3330, replacing an incorrect Atmel assumption |
| P5 | QCA6174 hw3.2 PCIe/ath10k_pci, firmware `ath10k/QCA6174/hw3.0`; not SNOC/WCN3990 |
| P6 | Establish KMS before glamor/freedreno; use the device's signed a530_zap |

At the time, build steps were setup-deps, setup-kernel, build-kernel and
build-bootimg. Recovery used the private full 6.1 boot backup under
`inventory/boot-backup/`. Early notes used base `0x80000000` and ramdisk
`0x84000000` because a roughly 42 MiB Image exceeded the old 16 MiB gap. The
October audit supersedes those header-only assumptions with actual LK addresses.

Initial scope excluded rebuilding Ubuntu/Klipper, touching residual LineageOS
system, flashing aboot/xbl or committing the approximately 51 MiB modem blob.
See [first boot](linux-7.0-bringup.md) and [hardware inventory](device-inventory.md).
