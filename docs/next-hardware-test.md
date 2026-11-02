# Further hardware tests after installation

Armbian boots from userdata ext4. Wi-Fi, SSH, Docker, ZRAM and reboot have
worked. The next priorities are sustained power, endurance and throughput.
An earlier DCP trial charged the battery and a short CPU/RAM test passed with
the 65°C passive trip. Later charger-reboot and Wi-Fi regressions remain open;
see the [latest report](stability-progress-2026-10-30.md) and
[initial progress](bringup-progress-2026-10-29.md). LAN still needs USB host and
adapter testing.

Android userdata was erased with authorization. The Android procedure below is
historical diagnostic guidance: restoring Android boot alone cannot restore
that data. It describes how to repeat early diagnostics after kernel/DTB
changes, rather than claiming every step remains untested.

1. When testing on an Android installation, first confirm Android is running,
   charge the battery and ensure physical Power access remains available. If
   boot hangs, hold Power for approximately 15–20 seconds until restart, then
   release it to return to the installed OS.
2. With Android and root ADB available, collect pstore/last_kmsg if supported.
   Store logs locally in a Git-ignored directory before clearing anything.
   Missing logs do not establish how far the previous kernel booted.
3. Recheck the Gemini identity/serial and verified boot/recovery backups. This
   is read-only and does not require formatting userdata.
4. Select a replacement diagnostic image only after LK effective addresses and
   the ARM64 wrapper pass inspection. Old candidates under
   `out/diagnostic-logging/` and `out/incompatible-stock-lk-2026-10-29/` exceeded
   LK's memory window and must not be used. See the
   [bootloader audit](bootloader-memory-2026-10-29.md).
   `boot-diagnostic-usb-debug.img` disables display, GPU, PCIe/Wi-Fi, UFS,
   charger and fuel gauge, and uses one CPU. It tests basic boot/USB only.
5. Use `fastboot boot` when physical recovery is available. Record fastboot
   acceptance separately from ACM enumeration and a functioning diagnostic
   shell. If available, collect `gemini-diagnostics` and full kernel logs.
   Fastboot `OKAY` is not proof that Linux booted. Start collection beforehand:

   ```bash
   python3 scripts/collect-diagnostic-console.py --usb-port 2-1 \
       --output out/hardware-2026-10-29/ram-boot-lk --timeout 180
   ```

   Recheck physical port `2-1` if the cable moves. The collector opens only
   `0525:a4a7` on the selected port and waits for `Gemini diagnostic` before
   issuing inspection commands. Do not assume `ttyACM0`; the audited laptop
   has three modem ACM ports. The collector does not reboot or flash.
6. After basic boot/USB succeeds, use the normal diagnostic image to inspect
   UFS, RAM, display, Wi-Fi/Bluetooth, temperature and power in stages. When
   preserving Android, do not format, run repairing fsck or mount userdata
   writable during diagnostics.

For the production server, prioritize Wi-Fi, SSH and light Docker workloads.
After real USB host/Ethernet and power tests, verify IPv4/IPv6 failover and
recovery using the [network policy](network-policy.md). Laptop routing
simulation does not replace driver/adapter testing.

If USB never appears, fastboot transfer alone cannot identify the cause. An
MSM8996 lk2nd candidate was downloaded and its upstream release hash verified
locally, but it has never been run or flashed. RAM boot evaluation and physical
recovery readiness would be needed first. One failed test does not establish
that replacing the bootloader is necessary.

Permanent rootfs installation is a separate step requiring adequate hardware
evidence and explicit userdata-erasure authorization. Offline package checks
alone do not establish that the image will boot on a phone.
