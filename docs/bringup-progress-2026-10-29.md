# Mi 5 Armbian progress — 29 October 2026

**Armbian is installed and running natively. Wi-Fi, SSH, Docker, ZRAM, repeated
reboot and a short CPU/memory test succeeded.** Build/boot targets were reached;
24-hour server readiness still requires endurance testing. This historical
report precedes the later [console/charging regressions](console-usb-2026-10-30.md).

Initial tests found insufficient laptop-USB power and missing CPU cooling maps.
A DCP charger raised battery 6% → 14%; cooling maps were added and the server
passive trip lowered to 65°C. A combined 128-second test with 512 MiB RAM data
completed without OOM, peaking at a sampled 81.3°C. Throttling reached 307 MHz;
this does not promise four cores running continuously at full clocks.

Installation followed explicit authorization to erase userdata and replace boot.
Android userdata was replaced by ext4. Boot/recovery backups do not restore
personal Android data. Recovery/aboot readback hashes remained unchanged.
This updates the [initial audit](audit-2026-10-29.md). The port uses the actual
Armbian framework and a local Gemini BSP; it is not official Mi 5 support.

## Native results

| Check | Result |
|---|---|
| System | Armbian-unofficial 26.11.0-trunk, Debian Bookworm arm64 |
| Framework | `5d0679d30533efdd32f421aaad2a98363cb9733d` |
| Kernel at this stage | `7.0.0-gemini-lk-dirty`, build #5 |
| Root | `/dev/sda14`, ext4 read/write; in-partition resize, 25G, about 20G free after Docker |
| Wi-Fi | Association, DHCP, default metric 100, Internet HTTPS |
| SSH | Root and `wkp` logins; host fingerprint checked through USB console |
| Reboot | Changed boot IDs; Wi-Fi, SSH, Docker and ZRAM returned automatically |
| CPU | Four cores; both policies `schedutil`, including after reboot |
| Docker | `docker.io` 20.10.24, ARM64 hello-world, cgroup v2, overlay2; `wkp` access |
| Container HTTP ingress | Laptop accessed a published phone-container port; test removed afterward |
| Short throughput | 16 MiB in 11.655 s, about 11.52 Mbps / 1.44 MB/s; one direction/sample |
| Container isolation | Alpine ARM64, 64 MiB/32 PIDs, matching `memory.max`; HTTPS before/after reboot |
| ZRAM | Armbian service active, approximately 1.3 GiB swap |
| CPU/RAM test | Up to 391.98% CPU and 514.9 MiB container memory; matching 512 MiB tmpfs checksums, no OOM; 128 s including verification |
| Charger | DCP, Wi-Fi/SSH without laptop USB, capacity 6% → 14%; charger reboot succeeded |
| Services | No failed systemd units after reboot |
| Identity | Unique host keys; first-login removed initial serial autologin |
| Protected partitions | aboot/recovery SHA-256 matched backups; boot prefix matched installed image |

DHCP assigned `192.0.2.10` during testing; it can change. Access was
`ssh wkp@192.0.2.10`. Unique credentials stayed in private local files under
`out/private-install-c7d53b75/`, excluded from Git/releases. The private Wi-Fi
profile retained the phone's factory MAC. Generic onboarding did not yet extract
that MAC from Android; driver default `00:03:7f:50:00:01` was observed, so generic
Wi-Fi identity needs checking on future installations.

## Required corrections

- Remove distribution-ABI-shadowing libraries/binaries. Userspace comes from
  consistent Armbian framework/distribution packages.
- Audit stock aboot's forced load addresses. The ARM64 wrapper places the
  kernel at `0x80200000`; memory span is 33,947,648 bytes including BSS with
  5,898,240 bytes DTB clearance. See [LK audit](bootloader-memory-2026-10-29.md).
- USB initially advertised 0 mA and charging was limited to 100 mA. Kernel #5
  advertises 500 mA and forwards DWC3 configured power to the charger. The host
  saw 500 mA; phone input limiter read 500,000 µA.
- Disable the old HUD/backlight for the initial server profile. HUD consumed
  about one-quarter of a core and offlined large cores when blank. Server
  setup brings all cores online and uses dynamic `schedutil`.
- Replace generic Armbian battery-zone CPU reporting with `cpu2-thermal`,
  falling back to `cpu0-thermal`. A post-reboot 58.4°C reading was only an
  instantaneous sample, not stable-load evidence.
- The four-core test exposed missing cooling maps for the 75°C passive trip:
  85.1°C after about 12 s. Maps enabled throttling, but a short retest still
  sampled 85.1°C before battery reached the 10% stop threshold.
- Final passive trip was 65°C. Combined charger testing lasted 128 s: about
  90 s sampling followed by checksum verification. Highest sampled CPU was
  81.3°C, last sample 74.2°C; the final hashing phase lacked continuous thermal
  samples. Both clusters reached minimum 307,200 kHz. No OOM; 512 MiB checksums
  matched. This checks one data pattern in part of RAM, not all memory.
- Persist 65°C in DTB; retain 110°C critical trip. Charger-only reboot passed;
  all four cooling bindings/trips were read back and container HTTPS worked.
  Post-boot: `running`, no failed units, 14% battery, instantaneous CPU 60.4°C.
- Mask Plymouth after quit timeout. Order `console-setup` after tmpfiles cleanup
  so temporary keymap files survive generation; native recovery was tested.
- Apply Wi-Fi 100 / Ethernet 600 to IPv4/IPv6. Mask the radio-cycling watchdog,
  generic GPT resize and old power guard.

## Validation and reproduction

The kernel passed 83 required settings. The server rootfs passed 29 checks,
including QEMU ARM64 programs, module metadata, identity, route policy, CPU
sensor and headless startup. All three boot images passed LK/DTB/initramfs/config
checks. Raw ext4, sparse roundtrip and both ZIPs were independently checked.
Stage reports are under `out/validated/` and `server-profile-pipeline.log`;
65°C updates are recorded in `thermal65-release-validation.log` and
`thermal65-provenance.log`. A stage passes only with `passed: true`.

Native evidence is separate in `out/validated/native-runtime-validation.json`.
Detailed install/onboarding/SSH logs are private. The installed image derived
from an earlier public build with private first-login and Wi-Fi provisioning.
Headless, sensor and console-order fixes were applied on-device and included in
later public builds. The generic public rootfs was not reflashed solely to match
hashes. Production boot later gained the cooling-map DTB with verified partition
hash; kernel Image/module ABI were unchanged. Provenance distinguishes offline
artifacts from runtime tests of a private derivative. Docker was installed on
the phone and is not bundled in the generic rootfs.

## Server limitations and next work

1. **Long-duration power under the real workload.** Laptop USB drained to 6%.
   After DCP at approximately 21:05 WIB, capacity reached 14% by 21:19 WIB;
   battery current around −1.26 to −1.45 A indicated charging. A 3 A driver
   limiter is not measured adapter current. Capacity stayed 11% during the short
   load sample; sustained-load power surplus remains unproven. No 24-hour,
   UPS or charge-only-limit claim.
2. **Size applications around throttling.** Full load can reduce clocks to
   307 MHz. Test actual light Docker apps, temperature, response and Wi-Fi for
   hours. The 128-second check is not endurance qualification.
3. **Keep throughput units explicit.** One result was 11.52 Mbps / 1.44 MB/s,
   below 10 MB/s. A negotiated 72 Mbps PHY rate is not application throughput.
4. **Physical backup LAN is untested.** USB host/role switching, adapter and
   power are required. Current USB is peripheral; ten laptop IPv4/IPv6 route
   cases validate metric policy only.
5. UFS clock gating, PSCI firmware, BAM and Wi-Fi board-file fallback warnings
   remain. I/O, association and containers work, but long-term power/stability
   effects are unknown. TWRP content checks passed without real recovery
   installation; actual installation used Fastboot. This server test did not
   qualify Bluetooth, GPU or visual display behavior.

Old LK-overlapping artifacts remain under
`out/incompatible-stock-lk-2026-10-29/` and must not be used.
