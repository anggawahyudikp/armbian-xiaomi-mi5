# Stability progress — 30 October 2026

Status: **preview; not qualified for 24/7 server operation**. No GitHub
publication has been performed.

31 October follow-up: [offline ext4 recovery completed](filesystem-recovery-2026-10-30.md).
Root writes, the startup fsck/remount order, Docker and Wi-Fi SSH passed.
Charger-only reboot and long-duration stability still require testing.

## Implemented improvements

- `mi5-doctor` reads an explicit allowlist of health data. Network addresses
  require `--private`. Missing hardware or commands do not fail the whole report.
- Login status shows battery, CPU temperatures, storage, interfaces and
  Docker/SSH services without a continuously redrawing UI.
- Root-only health samples every two minutes, with bounded history, timestamps,
  uptime and boot IDs. RTC initially showed 1970; Chrony corrected it after
  Wi-Fi connected. Early wall-clock timestamps must not be used alone.
- Optional Wi-Fi recovery targets one selected profile after at least ten
  minutes disconnected, at most three attempts per rolling hour. Active links
  and user choices are respected. No radio cycle or reboot. The native check
  while connected passed without retrying; prolonged outage recovery is untested.
- Publishing is blocked when hardware evidence is missing or a regression is
  unresolved. The publication-guard test does not contact GitHub.

## Test results

**20 server tests passed**, covering failed Wi-Fi attempt budgets, timeout,
missing hardware, LCD handling, USB lifecycle and publication guards.
**35 rootfs checks passed**, including rejection of private Wi-Fi profiles,
health history and personalized recovery configuration in generic images.

One normal USB reboot succeeded without reset/cable intervention. Kernel plus
userspace startup was **20.895 seconds**, excluding all bootloader/host USB
reconnection time. Docker, SSH, console and NetworkManager returned active with
zero failed units. Physical Power/Home testing after reboot remains pending
because the user could no longer reach the phone.

Wi-Fi autoconnected. Wi-Fi SSH succeeded at 08:28 WIB, with six DHCP renewals
logged by then; renewals continued at 08:32 WIB without recovery intervention.
Signal measured −87 to −88 dBm. This short observation does not establish
long-term reliability after earlier DHCP/handshake failures.

A resource-limited Alpine container stayed running during LCD sleep, with CPUs
0–3 online. Bind-mounted content remained readable after container restart;
no OOM was reported. The first HTTP attempt failed because the local Alpine
image lacks `httpd`; it was cleaned up and replaced by a process/data test.
This was not a network benchmark, backup restore or endurance test. All test
containers/data were removed and the prior display state restored.

The phone remained on laptop USB. At 08:32 WIB battery was **41%**, CPU readings
approximately **50.7–57.2°C**, main services active and no failed units. There was
no new charger trial. The driver's `Charging` label alone does not establish
net charging; current/capacity trends remain necessary. Auto-sleep stays disabled
on this test phone until physical wake after reboot is confirmed.

Three known local Wi-Fi/login secret values were searched in 212 nonignored
text files up to 2 MB each; none matched. The same values were absent from all
seven Git commits inspected. This is not an exhaustive audit of every secret;
release contents are checked separately.

## Evidence still needed

1. Power sleep/wake after reboot, and Home support.
2. Repeated USB/charger boots without cable/reset intervention.
3. Actual charging and 24-hour operation on a charger.
4. Better-signal Wi-Fi, outage recovery and 24-hour testing.
5. The selected Docker workload and backup/restore of its data.
6. Windows, physical LAN adapters and fresh package installation.

See the [stability plan](stability-plan.md) for criteria and tool usage. Private
evidence is under `out/stability-2026-10-30/`; do not upload it unreviewed.

## Built packages

Fastboot/TWRP were rebuilt and passed payload/checksum checks. Sparse expansion
matched the raw image. The boot hash remained identical to installed kernel #6;
this update did not flash the kernel again. The generic image was not freshly
installed, so native results cover file updates to the existing installation.
