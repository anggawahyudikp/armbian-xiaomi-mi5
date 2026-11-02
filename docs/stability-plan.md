# Stability gate before a public stable release

Version 0.1.0 passed the targeted acceptance gates; see the
[final report](stable-release-0.1.0.md) for scope and evidence. Passing these checks
does not establish 24/7 reliability. Do not publish credentials, private diagnostic histories,
original phone backups, or a personalized rootfs.

The user subsequently removed the 24-hour release criterion and requested
switching to the remaining tests. The paired duration run was stopped by that
instruction after approximately 28 minutes without observed failures; its
records are retained as a short observation, never a 24-hour pass. The current
release gate therefore covers the remaining targeted checks below. This change
is explicitly user-authorized; it does not change battery or thermal protection.

The user superseded the 2 November 17:00 WIB cutoff with “continue until
finished”. The former host and phone deadline timers are disabled. Testing
stops at or below 5% battery, or on a battery-read failure, through the native
workload guard; it never automatically powers off the phone. Restore the
current guard after a fresh installation, without restoring historical cutoff
timers. See the [current checkpoint](stability-status-2026-11-02.md).

The previous 1 November 23:59 and 2 November 06:00 deadlines are historical;
their cleanup results remain retained. The original host run has an independent
coverage gap after a laptop restart. The phone run later ended on a failed
DCP-source observation when the operator moved from charger to laptop USB.
Neither the segments nor their sum establishes the original 24-hour criterion.
Each new candidate needs separately identified boot and workload evidence.

| Area | Required evidence | Latest candidate limitation |
| --- | --- | --- |
| Boot | At least 5 consecutive USB boots and 5 charger-only boots, without cable/reset intervention | Earlier-revision counts remain historical; five charger-runtime rounds passed after immutable-file identity verification; policy-fixed generic first boot passed, and all five USB rounds passed |
| Boot diagnostics | Explain or correct observed findings before final assessment | Final kernel taint/ext4 errors zero and no failed units; repeated boots synchronized through NTP, saved time enabled; shutdown regression did not recur in the tested series; asserted alarm protection was harness-tested, not physically induced |
| LCD | Physical Power sleep/wake after each boot while server/SSH remains active; clarify Home behavior | Remote sleep has backlight zero; physical controls and text were operator-confirmed after all five final USB reboots; Home wakes the display without suspending the server |
| Power | Charger operation with battery trend, current and temperature recorded; 24-hour gate removed by user | DCP charging resumed under the 5% guard; five charger-runtime reboots passed and battery reached 68%; paired short observation stopped on user instruction |
| Wi-Fi | Repeated DHCP renewal and automatic recovery after AP returns; 24-hour gate removed by user | A completed passive 10-minute capture verified 11 REQUEST/ACK renewals; the paired short observation stopped on user instruction; controlled AP-return subsequently restored HTTP automatically in 10.0 seconds without reboot and restored original network settings; the earlier HTTP timeout remains retained |
| Throughput | User-revised minimum 0.5 MB/s on the current 2.4 GHz Wi-Fi uplink | Native ten-second transfers measured 0.652 and 0.588 MB/s, meeting the revised criterion; this is not a sustained 24-hour speed guarantee |
| Docker | Representative app workload, restart policy and persistent data survive reboot; 24-hour gate removed by user | Latest kernel passed six app/storage checks and a five-minute CPU/RAM test; the paired short observation ended without failures on user instruction; the earlier independent HTTP timeout remains retained |
| Storage | Consistent test-app backup/restore and filesystem observation | Original full backup verified; latest installed base passed app restore and SQLite WAL/integrity; generic first boot and application restore passed; final stopped-app/config snapshot verified off-device before cleanup |
| USB | Linux RNDIS/NCM and Windows RNDIS SSH without stealing host default route | Current runtime passed Linux NCM/RNDIS, DHCP, SSH and serial without changing host default routes; final-revision Windows11 physical USB passthrough passed both modes; policy-fixed generic onboarding passed; native PCs/Windows10 remain untested |
| Future LAN | Test selected adapter and failover before claiming the optional feature | Deferred hardware work, outside the initial Wi-Fi release |
| Install | Package checksums, fresh-image onboarding and verified recovery material | Charger-status base generic install passed; policy-fixed successor passed all offline validators and generic onboarding; all five USB reboots passed; full-system restore remains untested |

The counts and duration above are project acceptance criteria, not a guarantee
against future faults. Mark untested platforms/features explicitly rather than
claiming universal support.

## Scope of the first stable version

The current release target uses the existing battery, normal charging through
its USB port, Wi-Fi as the server uplink, LCD console and USB maintenance.
Direct supply through the battery connector and using USB-C for a physical
LAN adapter are deferred hardware work. They are not prerequisites for the
Wi-Fi-first release and must not be advertised as validated features.
Windows 11 build 26300.9457 passed both modes with the real phone passed through
to QEMU. This verifies that Windows kernel and its class drivers; it does not
establish native-PC or Windows 10 behavior. Any stable label must state the
actual tested release scope.

## Diagnostics

- `mi5-doctor`: battery, temperature, services, free space and interfaces.
- `mi5-doctor --json`: allowlisted report without SSID, MAC, IP, hostname,
  connection profiles, environment, or full journals. Review before sharing.
- `mi5-doctor --private --json`: adds local addresses and boot ID for local audit.
- `mi5-health.timer`: private snapshot every two minutes, approximately 4 MiB
  maximum history plus one record, two rotating files in `/var/lib/mi5-health/`.
  Directory mode 0700, files 0600; do not upload them unreviewed.
- `systemctl disable --now mi5-health.timer`: stop periodic collection.

These commands observe the system. They do not reboot, change charging controls,
cycle Wi-Fi, or modify CPU policy. Login status does not continuously redraw the
screen or wake the LCD. Both the test phone and generic image now use a
300-second display timeout. Automatic sleep and remote wake were verified;
physical Power/Home and visible Linux were operator-confirmed after each final USB reboot. Use
`sudo mi5-config display wake` over SSH for remote wake. See the
[dated acceptance report](stability-acceptance-2026-10-31.md) for measured scope.

## Safe recovery and backups

Keep USB SSH (`192.168.7.2`) available during network tests. Save a matched boot
image/module backup before kernel changes. Never flash a boot image with modules
from another build merely because the kernel release string matches.

For application backups, use the database's own consistent export or stop the
application before copying its data. Store Compose files and secrets separately;
keep an encrypted copy off the phone. Test restoration into a separate directory
before overwriting live data. Application-specific automation will follow the
choice of workload, storage paths and backup destination.

## Bounded Wi-Fi recovery

The old radio-cycling watchdog remains masked. The new optional
`mi5-wifi-recovery.timer` retries only one explicitly selected saved Wi-Fi UUID:

1. Find the profile UUID with `nmcli -g connection.uuid connection show PROFILE`.
2. Set `PROFILE_UUID=...` in `/etc/default/mi5-wifi-recovery` and confirm the
   `INTERFACE`. Leave UUID empty to disable all recovery actions.
3. `sudo systemctl enable --now mi5-wifi-recovery.timer`.

It waits for a disconnected state observed for at least ten minutes, attempts
at most three activations per rolling hour with ten-minute minimum spacing,
and does not touch an active/activating connection, a disabled radio, a profile
with autoconnect disabled, or a user-disconnected device. Failure and timeout
consume the same budget. There is no radio toggle, NetworkManager restart,
USB change, or reboot. For planned maintenance stop the timer first:
`sudo systemctl stop mi5-wifi-recovery.timer`.

This is recovery assistance, not a fix for weak RF, a broken DHCP server or a
wrong password. Its private runtime budget resets after reboot. The generic
image ships with an empty UUID and timer disabled; the test phone opts in to its
existing profile. NetworkManager already has its own retry mechanism; see the
[official connection settings](https://www.networkmanager.dev/docs/api/latest/nm-settings-nmcli.html)
and [device state reasons](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-dbus-types.html).
