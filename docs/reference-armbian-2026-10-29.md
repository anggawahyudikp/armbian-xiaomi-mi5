# Lessons from a reference Armbian server — 29 October 2026

The authorized SSH inspection was read-only. No packages, services, files or
workloads were changed. Connection details and credentials are not included.

| Component | Observed result |
|---|---|
| Distribution | Armbian 23.08.0-trunk, Debian 12 Bookworm |
| Hardware/family | Amlogic S905x; rebuild metadata meson-g12b/meson64 |
| Kernel | `6.1.52-ophub` |
| Userspace ABI | Debian GLIBC 2.36 |
| NetworkManager | 1.42.4, enabled at boot; systemd-networkd masked |
| SSH | OpenSSH 9.2, enabled |
| Systemd | 252 |
| Armbian packages | BSP, armbian-config, firmware, plymouth-theme, zsh |
| Memory | Approximately 1.9 GiB RAM; 965 MiB ZRAM swap plus swapfile |
| Logging | Separate 50 MiB ZSTD ZRAM for `/var/log`; armbian-ramlog active |

Applied to the Mi 5 port:

- Keep Debian 12 ABI consistency; do not copy libraries/binaries from another
  distribution into Bookworm.
- Use framework BSP and `armbian-config`, retaining Armbian first-login/firstrun.
- Use Armbian's ZRAM/ramlog implementations. Build ZRAM as a module so services
  can select swap/log device counts. Local settings choose size and algorithm.
- Use NetworkManager as the single network manager. Route priorities do not
  prove physical USB host support.
- Leave general tuning and user management to Armbian; keep the overlay
  specific to the phone.

Hardware differences:

- The reference uses U-Boot and SBC storage; Mi 5 uses Android boot images, LK
  and an existing Android GPT that must remain intact.
- Mask generic partition resizing. `gemini-resize-root` only runs `resize2fs`
  inside the existing userdata partition.
- Verify DTB, kernel, charger, USB role, Adreno/QCA6174 firmware and reboot on
  the actual phone. Reference-server success does not validate these.
- Do not copy `commit=600,data=writeback` as a power-loss guarantee. Mi 5 uses
  normal ext4 journaling with `noatime` pending power testing.

The local snapshot is `out/reference-armbian/inventory.txt`. The reference was
not used as a complete rootfs donor; its SSH identity, accounts and live data
are excluded from the Mi 5 image.
