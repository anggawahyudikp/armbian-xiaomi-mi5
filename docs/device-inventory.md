# Xiaomi Mi 5 (gemini) inventory

> Historical August 2026 Linux/Ubuntu record. Current installation and load
> rules are in the [flash guide](flash-guide.md) and
> [LK memory audit](bootloader-memory-2026-10-29.md).

Recorded 2026-08-27 from TWRP. Device serial, WLAN MAC, and filesystem UUID are omitted from the public tree.

Not Android at runtime: `boot` is a mainline-style Linux image; `userdata` is the Ubuntu root. `system` still has LineageOS 17.1 and is unused.

| Part | Block (typical) | Contents |
|------|-----------------|----------|
| boot | sde36 (64 MiB) | Linux + initrd |
| recovery | sde37 (64 MiB) | TWRP 3.7.0_9-0 |
| system | sda14 | Leftover LineageOS 17.1 |
| userdata | sda15 | Ubuntu root |
| modem | sde35 | Qualcomm firmware |
| persist | sda12 | MAC / calibration |

SoC MSM8996 (Kryo 2+2), UFS `624000.ufshc`, panel JDI FHD R63452 command mode, GPU Adreno 530, Wi-Fi QCA6174 PCI. Touch is Synaptics S3330 / rmi4, not Atmel.

Previous live kernel was `6.1.14-umeko-rv0` (msm8996-mainline family). USB gadget CDC ACM `0525:a4a7`.

## Historical configuration details

These August partition numbers are not the October phone's layout. Always use
verified GPT labels; October userdata was sda14. The old system was Ubuntu
20.04.6 LTS, hostname `XiaoMi5-Ubuntu`, user `umeko` with sudo and GECOS `redmi2`.
It hosted Klipper, Moonraker, Fluidd, KlipperScreen, 1Panel and Docker/containerd.
SSH was enabled with UFW allowing 22. `autottyGS0` used `login -f umeko`.

The 6.1 package supplied 572 modules and `/boot/vmlinuz`, config, System.map and
initrd. Main configuration included Qualcomm clocks/pinctrl/interconnect,
UFS built-in, MSM/JDI modules, configfs serial/ECM/RNDIS, ATH10K_PCI and
48-bit ARM64 VA. ATH10K_SNOC was off. Atmel was configured but the actual touch
controller was Synaptics S3330. Soft dependencies loaded the panel before DRM
and cfg80211 before ath10k_pci. DRM reported 1080×1920 `msmdrmfb`, although
Xorg used simplefb without glamor. The previous Xorg log was dated 2025-12-14.

Kryo CPU parts were `0x211` Silver and `0x205` Gold, implementer `0x51`, four
cores total. Hardware revision was 1.4.0, design battery 3000 mAh. Original
boot was Android header v0, 4096-byte pages and kernel header `0x80008000`.
LK cmdline identified UFS `624000.ufshc`, orange verified state and the
`mdss_dsi_jdi_fhd_r63452_cmd` single-DSI panel.

Device firmware included a530_zap components, mba/modem/slpi/venus, with ADSP
missing. Residual LineageOS 17.1 / Android 10 (SDK29, 2020-11-19) used system
and cust but did not participate in Ubuntu boot. TWRP USB was `2717:ff68`;
running Ubuntu exposed `0525:a4a7` serial. Identifying/calibration data and
filesystem UUIDs remain omitted from this public inventory.
