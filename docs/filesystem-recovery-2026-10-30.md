# Charger recovery and ext4 failure — 30 October 2026

Updated 31 October: **offline filesystem recovery completed; hardware stability
regression remains open**. The offline recheck passed, the boot-order fix is
installed, and root writes, Docker, health recording and Wi-Fi SSH work again.
The sections below preserve the investigation; the completed recovery is
recorded in the final section. No formatting or reinstall was performed.

## Charger and Wi-Fi observations

At 19:42 WIB, Wi-Fi SSH returned at the existing address on boot ID
`310cb252-ea1c-45f6-a07a-5a872b276608`, uptime approximately 11 minutes.
The phone reported DCP, online=1, a 3 A configured input limit, 84% battery and
−895,838 µA battery current. At 19:48:58 WIB capacity reached 89% with
−606,075 µA. Negative current and rising capacity demonstrate charging during
this session; the 3 A setting is not a measurement of adapter current.
Wi-Fi was connected with DHCP IPv4 and −86 dBm signal. Charging and Wi-Fi can
therefore operate together in this setup. The earlier connectivity failure's
cause and whether this boot required physical intervention remain unverified.

## Filesystem failure

Eight units were failed, including Docker, health recording, hardware monitoring,
random seed, logrotate, vnstat and apt maintenance. Docker and health recording
explicitly failed with `Read-only file system`.

Root mount options included `rw,noatime,errors=remount-ro,emergency_ro`:
the emergency read-only state prohibited writes despite the displayed rw flag.
Kernel logs showed:

```text
warning: mounting fs with errors, running e2fsck is recommended
ext4_validate_block_bitmap: bg 2: bad block bitmap checksum
Remounting filesystem read-only
```

The superblock reported `clean with errors`, needs_recovery, 252 filesystem
errors, an initial ext4_orphan_get EFSCORRUPTED entry and a later bitmap-checksum
error. Its mount counter is not a reliable count of user-triggered reboots.
Battery depletion/restarts preceded this discovery, but causation has not been
established. Do not force a writable remount or run repairing fsck on mounted root.

## Preserved evidence and backup

Private local evidence is under `out/charger-recovery-2026-10-30/` (mode 0700).
A verified 20,067,370-byte archive with 3,505 entries preserves configuration,
user files, logs, health history, NetworkManager state and existing Docker
volume paths. It is not a complete raw filesystem or image-layer backup.
Archive SHA-256:
`27c98a4b89f5c845cd54b5a49d92daf3588b201592de56ad9ae81b49b0c18380`.
It contains private material and must not be published.

Recovery partition SHA-256 still matched the original backup:
`6d0c2afeacec9e83e90b3027a556346bf4dc86685af3438d308da2dbe391911d`.
Its ramdisk contains e2fsck but no TWRP marker was found; do not assume it is a
validated TWRP recovery environment.

## Boot-order correction prepared in source

The production init previously mounted the identified root writable before
switch_root. The actual `systemd-fsck-root.service` was then skipped because its
`ConditionPathIsReadWrite=!/` condition failed. This explains why startup did
not perform the standard root check.

The init now keeps the identified production root read-only, allowing journal
replay only after the existing noload identity probe. It then hands off to
systemd, whose fsck-root service precedes remount-fs and normal writable startup.
Unidentified/F2FS userdata and RAM diagnostics retain their existing protections.
Tests verify both the initial noload probe and the final read-only handoff.
Boot/installer/layout tests and all 20 server tests passed. At preparation time
the correction was not installed; the 31 October section records its subsequent
installation and hardware verification.

## Prepared recovery artifacts

Isolated artifacts are under `out/charger-recovery-2026-10-30/fsck-boot/`:

- `boot.img`: production candidate with read-only handoff for systemd fsck.
- `boot-filesystem-rescue.img`: RAM diagnostic with Debian ARM64 e2fsck 1.47.0
  and its complete shared-library closure. It keeps internal block devices
  read-only and mounts no userdata by default.
- `mi5-fsck-check` inside the RAM image checks the expected filesystem UUID,
  verifies the partition is unmounted and uses `e2fsck -fn` only. It never
  enables block writes or repairs automatically.

The e2fsck executable ran under ARM64 emulation and checked a disposable clean
ext4 fixture. Both images passed LK layout, required kernel settings and
initramfs inspection. These are preparation checks, not a completed recovery.

The planned hardware step needed USB data and a temporary reboot into the RAM
image. Inspect filesystem errors first, then determine repair from the report.
Verify a clean offline check before normal boot, and subsequently confirm root
write access, fsck/remount ordering, Docker, health recording, Wi-Fi and charging.
No userdata formatting or reinstall is part of this plan.

## Ordinary reboot requested at 20:26 WIB

The user requested trying a normal reboot before filesystem recovery. The
command was accepted over SSH with battery 99% and DCP connected. The existing
boot image was retained; no fsck or repair was performed. SSH/ping did not return
during the initial observations, and LAN SSH discovery found no matching Mi 5
host key. A new boot ID and post-reboot filesystem state remain unverified;
physical display confirmation is pending. This does not identify whether the
phone stalled during shutdown, boot or network initialization.

## USB follow-up — 31 October, 02:30 WIB

The user connected USB data and confirmed also holding Power/restarting before
this boot. USB SSH and Wi-Fi returned on boot ID
`41e5b800-1dc8-4c06-aeb5-76e67cc6cc90`; this is not proof that moving the cable
alone restores boot. Battery read 99%, then 98%, on SDP/500 mA with positive
discharge current. The same ext4 bitmap error and emergency read-only root
remained, with seven failed units. Logs were saved locally; the larger kernel
journal transfer timed out and its saved copy is partial.

The direct bootloader reboot helper was invoked. Stable LK USB fastboot was not
verified and the phone returned to composite Armbian USB mode. Pending read-only
fastboot queries were terminated. No RAM image was booted and no filesystem
check or repair ran. Physical Volume Down + Power remains the available fallback
before proceeding with the prepared RAM recovery workflow; software bootloader
entry has not been established for this installed kernel/firmware combination.

### Software entry follow-up

Read-only inspection confirmed that the installed bootloader reboot helper has
the same SHA-256 as the validated utility
(`2957fe58265d5c46e2f5c7d65001f997aa44b2e9d00141d64df8f688d1ab9345`).
The running device tree identifies the PON controller as `qcom,pm8916-pon`,
provides `mode-bootloader = <2>`, and has a bound qcom-pon driver. This confirms
the configuration and driver binding, not successful delivery or retention of
the boot reason. The current boot uses cold reboot mode and firmware reports
PSCI v1.0. The exact reason for returning to Linux remains unresolved.

The existing BCB command reads `bootonce-bootloader`; that marker alone did not
produce verified fastboot. No repeat BCB write, MMIO workaround, additional
reboot, or filesystem repair was performed during this follow-up. Recovery
artifacts remain prepared but unbooted.

## Completed offline recovery — 31 October

The user entered fastboot physically. USB `18d1:d00d`, serial `c7d53b75` and
product `MSM8996` were verified against the already audited phone identity.
The first RAM-image transfer failed with a USB protocol error. A USB reset
targeted only this verified device, after which `fastboot boot` succeeded.
The diagnostic console then confirmed the expected running kernel and RAM init;
detected internal block devices were read-only and userdata was unmounted.

The first inspection helper stopped before fsck because Debian BusyBox did not
include its linked `blkid` applet. The fallback verified the expected userdata
GPT label, ext4 magic, filesystem UUID, unmounted state and read-only block flag
using supported tools and direct superblock reads. The full read-only check
returned 4 and reported bitmap checksums, inode bitmap differences and incorrect
free-space counters. It did not report duplicate inodes or directory-structure
damage; journal recovery was deliberately skipped in this read-only pass.

With the existing configuration backup reverified, `e2fsck -p` replayed the
journal and completed conservative repairs, returning 1. Writes were enabled
only for the selected userdata device and its parent disk; the read-only flags
were restored afterward. A subsequent forced `e2fsck -fn` passed all five
stages and returned **0**. No format or reinstall was performed.

The 983,040-byte e2fsck undo file was copied into a private local directory and
its SHA-256 verified:
`9fc580a87dc516390f95a9f628f18e8865a32d353b9d00226989626c8d0f421d`.
The undo file is private recovery material, not a replacement for the backup.

The existing boot prefix matched the preserved previous production image.
The corrected production boot was uploaded to RAM, hash-verified, written only
to the verified boot partition, and read back with matching SHA-256
`4f0d7c80b66fcf88a51e1880abebe44226a2ec29402b3e9da59c63b14507e417`.
The installed kernel remains build #6; this change is in its initramfs.

One normal reboot from RAM recovery returned to Linux without another physical
reset. Boot ID: `c1d27a97-1d94-4e5b-9d06-ee7862137fb0`.

- `systemd-fsck-root.service` ran successfully with its condition satisfied;
  its journal reported rootfs clean.
- Kernel messages show the identity probe, read-only production mount and then
  systemd's writable remount, without the previous emergency read-only flag.
- An actual create/write/delete probe under `/var/tmp` passed. The superblock
  reports `clean`, and no new ext4 error was observed in this boot.
- Docker 20.10.24, overlay2 and cgroup v2 returned. A cached ARM64 Alpine
  container ran with a 64 MiB limit, wrote and read a temporary file, and exited.
- The health service returned success and resumed its bounded private history.
- USB SSH and regular-user Wi-Fi SSH at `192.0.2.10` reached the same boot
  ID. English SSH locale remained effective.

One failed unit remains: `NetworkManager-wait-online.service` timed out during
startup. Wi-Fi subsequently obtained its address, but the observed signal was
about −90 dBm. This failed state was retained as evidence. The clock initially
showed 1970 and corrected after networking returned; boot IDs and uptime are
needed when interpreting the logs.

Battery fell from 37% during RAM recovery to 27% during the follow-up checks on
laptop USB, despite its charging status text. No heavy load test was run.
At 06:11 WIB, battery was 25%, temperature 25.2 C and root remained writable
after about 17 minutes of uptime, with Docker, SSH and the health timer active.
Moving back to a charger, preferably with improved Wi-Fi reception, was requested
before prolonged operation.

### Artifact validation follow-up

The initramfs builder no longer creates the unsupported `blkid` link. Boot image
inspection now executes the packaged ARM64 BusyBox and verifies that every
linked applet exists. The previous image is rejected by this new check, as
expected. Rebuilt production and diagnostic images pass the stronger check.
The running recovery-tested boot retains the older unused link; its init
program and kernel are unchanged by this link cleanup. Exact image identity is
recorded separately from the new generic release artifacts.

Both local release ZIPs were updated with the rebuilt boot payload and their
checksums, preserving the unchanged rootfs payloads. Full archive validation
passed, and the seven-artifact checksums and build provenance were refreshed.
The two native init safety modes, 13 installer tests, 9 layout tests and all
20 server tests passed. Generic image installation remains a separate hardware
test, and these artifacts were not published.

The private filesystem rescue image was also rebuilt with the supported-tool
identity check and passed ARM64 tool execution and image validation. The exact
RAM image used during this recovery is preserved separately as
`boot-filesystem-rescue-used-2026-10-31.img`; the rebuilt rescue image itself
has not been booted on hardware.

Charger-only reboot, repeated boot acceptance, LCD buttons after reboot,
controlled Wi-Fi outage recovery, a 24-hour charger/application soak, Windows
host support and a fresh generic-image install remain unverified. Publication
remains blocked by the hardware stability gate.
