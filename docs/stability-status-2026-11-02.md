## Final assessment — 3 November 2026

The targeted gates are complete. See the [0.1.0 stability report](stable-release-0.1.0.md) for current status, metadata-only promotion and limits. All checkpoints below are historical and retain their original pending/failure states; they do not describe the current release.

Final USB reboot series: all five consecutive reboots of the final generic image passed. Round 5 was ready in 94.86 seconds with 77% battery. Five distinct boot IDs, baseline continuity and nonregressing application counters were verified. Physical controls and visible Linux are operator-confirmed for rounds 1–4; round 5 remains pending. Release assessment and test cleanup remain open.

USB checkpoint: four of five consecutive final-image reboots passed. Round 4 was ready in 54.79 seconds at 78% battery, with boot continuity and persistent application counter verified. The operator confirmed physical controls and visible Linux after round 3. Physical confirmation after round 4 and the final reboot remain open.

USB reboot update: 3 of 5 consecutive final-image reboots passed. Round 3 was ready in 65.22 seconds with 78% battery; boot continuity and persistent application counter were verified. Physical Power/Home and visible Linux confirmation is pending for round 3. Stable qualification remains open.

Physical check update: the operator confirmed Power/Home operation and visible Linux after USB reboot 2. Both completed reboot rounds now have operator confirmation; native round-2 capture missed the action window. USB reboot 3 is being tested; stable qualification remains pending.

# Stability checkpoint — 2 November 2026

Status: **community preview; stable qualification remains open**.
The user authorized continuation until completion, superseding the former
17:00 WIB cutoff. Both historical cleanup timers are disabled. The native
battery guard remains active with a 5% stopping threshold and no automatic
poweroff. Short runs cannot establish the original 24-hour requirement.

## Final generic installation and package-service correction

The cleanly installed getty-fix image completed normal serial onboarding.
Installing Docker exposed an inherited build-only `policy-rc.d` stub that denied
all package service starts. The project now removes only that exact regular-file
stub and rejects it during rootfs validation. Custom policies and symlink targets
are preserved; three regression cases and 46 rootfs checks passed.

The corrected generic image was rebuilt and flashed successfully. All three
boot images, kernel and DTB remain byte-identical; the rootfs and both installer
archives were regenerated and validated. Normal serial onboarding then passed
on the expected new root UUID. Docker and containerd started directly from
package post-install scripts, before an explicit start command. Consistent
application data was restored and authenticated Linux USB serial passed.
Two consecutive USB reboots have passed, in 67.6 and 53.6 seconds, each with
retained application data, Wi-Fi SSH/HTTP and clean filesystem/service checks.
The [current measurements](measurements/2026-11-02/final-generic-initial-runtime.json)
retain the remaining three reboots, per-boot physical checks and Windows tests.

The operator confirmed physical Power/Home and visible Linux text after the
first of those USB reboots. Its native observer expired before the action was
captured, so that round uses operator confirmation rather than a claimed native
button trace. The second physical confirmation is pending. The earlier fresh
installation did capture Power/Home events, backlight changes and uninterrupted
local HTTP over five minutes, alongside the operator's visual confirmation.

A cable movement was followed by descriptor/setup-address failures on the
original laptop port. Reconnecting to another port restored enumeration, USB
SSH and backup transfer. This incident and its failed recovery attempts are
retained; the underlying physical/controller cause is not conclusively isolated.
The Windows test VM's first session subsequently shut down before phone
passthrough; it was restarted independently. No final-revision Windows USB pass
is claimed from its earlier successful OS inventory.

## Final-image Windows USB regression completed

Both real-phone modes passed with Windows 11 build 26300.9457 under QEMU:
RNDIS revision 0102 and NCM revision 0103. The checks verified signed Microsoft
class drivers, DHCP from the phone, no USB DNS/default route, preservation of a
nonempty controlled virtual default route, pinned-key SSH with and without PTY,
application HTTP and the actual ACM Linux console. Real Microsoft descriptors
and remote-wakeup flags were preserved. This does not verify native Windows
PCs or Windows 10; see the [scoped Windows results](measurements/2026-11-02/windows-final-usb.json).

A late post-capture mode check found that the automatic RNDIS fallback had
already run. The NCM serial response itself was independently placed before
the fallback using the same boot's monotonic journal timestamp and a bounded
host clock sample: it completed at least 4.58 seconds beforehand, with a
6.55-millisecond sampling round trip. The initial observer failure is retained;
no hardware pass was inferred merely from the eventual RNDIS mode.

Temporary phone authorization was revoked. The RNDIS USB-node ACL was restored;
the NCM node had disappeared during re-enumeration, removing its temporary ACL.
The guest shut down before online key-removal verification, so its matching test
key was removed offline from the stopped private Windows image, with the guest
partition identified explicitly. The temporary mount/NBD mapping was removed,
the host private test key and secret payload deleted, and VM/TPM units stopped.
The phone returned to RNDIS; a post-test probe found the expected root UUID,
zero kernel taint/ext4 errors, no failed units, working HTTP and an active
5% battery guard. Battery was 78% at that checkpoint.

Two USB reboots remain verified. Physical round two is awaiting the operator;
its initial input window expired without button events. A fresh observation
window on the same boot is active. Three further USB reboots and their physical
checks remain before assessing the stable gate.

## User-authorized duration change

The user removed the 24-hour criterion and requested proceeding to other tests.
The independent and native recorders were stopped after approximately 28 minutes
without observed failures. The application and battery-floor guard remain
active. These are short-run results, not a completed 24-hour qualification.
See the [retained duration revision](measurements/2026-11-02/duration-criterion-revision.json).
All other release gates remain active except the separately revised throughput
criterion. USB access is currently unavailable, so network recovery testing is
being prepared with automatic rollback.

## Current-runtime AP-return test

The controlled AP test passed while the phone stayed on its charger. With the
AP disabled for 35 seconds, external HTTP became unavailable as expected.
After the AP returned, HTTP recovered automatically in 10.0 seconds on the same
Linux boot, with advancing persistent application data. The primary Wi-Fi
profile and original autoconnect flags were restored, the temporary profile
removed, and the battery guard remained active. Host forwarding and default
routes were restored. See the [sanitized result](measurements/2026-11-02/ap-return-current.json).

A new consistent configuration/application/diagnostic snapshot was captured
with the application stopped, copied off the phone, and verified against its
source SHA-256. The 1,987,913-byte archive contains 243 entries and was reopened
successfully on the host. The application resumed and external HTTP was
verified afterward. This private snapshot contains credentials and is not a
public artifact or a full-userdata restore test. Refresh it immediately before
any final wipe; see the [sanitized snapshot record](measurements/2026-11-02/pre-final-snapshot.json).

## Charger and release-artifact update

The battery guard actually stopped test workloads at 5% during the USB reboot
check. After the operator connected a DCP charger, charging was verified before
explicitly resuming the workload. One diagnostic charger reboot returned Linux,
Wi-Fi, SSH and the persistent Docker application without physical intervention.
This is one diagnostic result, not the required five formal charger rounds.
The latest power observation recorded 56%, charging, 24.7 C, and no failed units.

The final generic artifact was rebuilt using the bundled, pinned boot packager.
All three boot images match the preceding candidate byte for byte; offline
validation passed. The installed system has the same production boot image and
runtime USB corrections, but its root filesystem UUID differs from the new
image. A remote comparison of 38,972 release files passed after aligning three configuration files. The original differences and both comparison results are retained privately. This verifies the selected file hashes, symlink targets and modes; it does not replace
fresh-image onboarding verification, which remains pending USB availability.
Current runtime qualification can proceed through Wi-Fi while on the charger.

Five consecutive charger-only runtime reboots subsequently passed without
physical reset or cable intervention, with verified readiness in 59.5–61.0
seconds. Each round checked boot identity, writable/error-free root filesystem,
services, NTP, Wi-Fi user SSH and HTTP, persistent application data, DCP charging
and a remote LCD cycle. Battery increased from 65% to 68%, with battery
temperature 25 C. Physical buttons and rendered output remain separate checks.
See [the sanitized results](measurements/2026-11-02/charger-runtime-five-boots.json).

A new 24-hour charger/Wi-Fi/Docker run has started with native minute sampling
and independent host SSH/HTTP observations. Its initial complete sample passed;
this is an active run, not a completed duration result. It covers the installed
runtime whose selected release files matched, while generic first-boot
qualification remains open.

The additional passive DHCP observer completed 600.2 seconds without errors.
It captured 11 matching REQUEST/ACK transactions on 120-second leases, with
no observed request lacking an ACK. This verifies repeated renewal on the
current runtime; it did not induce an AP outage or verify AP return. See the
[complete DHCP result](measurements/2026-11-02/charger-runtime-dhcp-complete.json).
The simultaneous independent soak had 15 complete samples over about 14 minutes
without failures at that checkpoint; the required 24 hours remains open.

## Runtime progress after the user's 5% authorization

The user explicitly authorized phone testing until the battery reaches 5%,
superseding the earlier 30% preflight. A persistent native one-second guard
stops owned test services and containers at or below 5%, on a battery-read
failure. It does not power off the phone. The guard
source passed five simulated boundary/error/deadline cases; its real battery
floor was subsequently verified on hardware as recorded above.

The installed charger-status kernel completed a 300.8-second CPU/RAM test with
two 128 MiB workers. Each verified its memory hash for at least 300 seconds
(988 and 994 iterations). Maximum sampled CPU temperature was 71.6 C and battery
temperature 25.5 C; battery readings went from 10% to a minimum of 6%. This passes
the project's 85 C bounded-test criterion. It would still exceed the older
70 C conservative diagnostic guard, so those earlier stopped results remain
retained rather than being relabeled as passes. This is not a 24-hour result.

All six application/storage checks passed: container hardening and limits,
bridge DNS/HTTP, restart persistence, stopped-application backup/restore,
SQLite WAL crash rollback/integrity, and continued local HTTP. The newly copied
SQLite backup independently passed host integrity and contained 16 committed
rows. Remote LCD sleep/wake preserved CPU availability and HTTP service;
physical buttons and visible rendering remain unverified for this revision.

Independent Wi-Fi HTTP observation recorded 160 successful responses and one
three-second timeout in 161 samples. Its recording began after CPU work had
already started, leaving an explicit initial coverage gap. The timeout's cause
is unresolved: the inspected native window contains a successful DHCP renewal
and no kernel messages, not proof of a particular fault. Do not claim a fully
passing independent network run from this sample.

Native Wi-Fi throughput was 0.652 MB/s phone-to-host and 0.588 MB/s in reverse,
with routing verified through wlan0. The original 10 MB/s criterion was not met.
The user subsequently revised it to a minimum 0.5 MB/s on the current 2.4 GHz
network, which these short-transfer results satisfy. The raw original result
remains unchanged; see the [criterion revision](measurements/2026-11-02/wifi-throughput-criterion-revision.json).
Post-load inspection found zero kernel taint, zero ext4 errors, a successful
fsync write, no failed systemd units, and the application running without OOM.
The latest probe read 7% battery; an earlier post-load reading rebounded to 8%.
Neither reading alone establishes a sustained charging trend.

The rootfs-only rebuild completed successfully at 12:09 WIB. All seven offline
validators passed and frozen inputs matched. The kernel and boot binaries are
byte-identical to the tested base, while the new generic rootfs has a different
UUID and includes the console changes. That rootfs has not yet been freshly
installed or first-boot qualified. See the [runtime record](measurements/2026-11-02/runtime-floor5.json)
and [new generic candidate](measurements/2026-11-02/getty-wait-cr-candidate.json).

## Earlier installed-base checkpoint

The new kernel build finished successfully at 08:39 WIB. All frozen build
inputs matched at completion, and the boot images, matching modules, rootfs,
sparse roundtrip and both release archives passed their offline validators.
The diagnostic image RAM-booted with zero taint, all internal block devices
read-only, no internal filesystem mounted, and the expected cooling maps.

The matching generic image was installed successfully. Userdata took 217.574
seconds and boot took 0.729 seconds. Normal Armbian onboarding completed,
English UTF-8 and Asia/Jakarta were selected, strong root credentials were set,
and authenticated regular-user Wi-Fi SSH passed. The host key was initially
pinned over the verified direct physical USB network and then independently
matched to the public key read during an authenticated serial session.

First boot exposed an additional USB-console issue: the standard authenticated
serial getty started and then stopped, while USB SSH remained available.
A manual getty restart restored authenticated serial login. A warm USB rebind
on the original code also passed, so the first-boot cause is not yet established.
A bounded udev-event-settle change passed 25 service tests; its runtime test
and inclusion in a new coherent generic image remain separate work. During
runtime deployment, a private helper accidentally removed executable permission;
the permission error and subsequent stale-gadget start failure are retained.
The executable permission was restored, stale gadget state was removed,
and USB/DHCP/getty recovered. An intermediate serial authentication attempt
failed with a corrupted login prompt. A separate authenticated getty drop-in
now waits for Enter before showing the banner; subsequent regular-user serial
login passed. At that checkpoint the new rootfs was being packaged with both changes;
the completed result is recorded in the newer section above.
These results do not yet prove a corrected generic first boot.

The initial image clock was four days behind and NTP corrected it once Wi-Fi
was restored. Read-only inspection confirms that the raw PMIC RTC is not UTC;
RTC-to-system initialization is intentionally disabled. The enabled
`fake-hwclock` service restores a saved timestamp early and saves on orderly
shutdown. Its saved file now contains the corrected date, and the periodic save
is configured. Subsequent-boot clock behavior still needs hardware verification;
this is not a claim of accurate offline UTC timekeeping.
After verified offline Docker package installation, the battery read 12%.
A health sample during setup recorded 377 mA net discharge; later idle samples
recorded about 9 mA net charge while capacity stayed at 12%. Docker/containerd
were stopped and the LCD backlight was verified off. The user subsequently authorized device testing above 5%, superseding the
earlier 30% preflight, with testing stopped at or below 5%. A persistent
one-second native guard now stops owned test services and containers at that
floor or the existing deadline, without powering off the phone. Its actual
source passed simulated 6→5, 5, 4, read-error and deadline cases. Docker and
application validation have resumed under this guard; no passing result is
claimed before inspecting their output.
No DCP/charger-only qualification or full-duration pass has been established
for this revision. See the [candidate record](measurements/2026-11-02/charger-status-candidate.json).

## Resumed investigation after the deadline extension

The user extended testing to **17:00 WIB on 2 November**. The host cutoff is
rearmed for 16:59, and the matching phone timer installer is prepared for the
next Linux installation. The earlier 06:00 cutoff below is historical.

A status-aware charger interrupt fix passed all 23 server tests, including all
256 live status values and six read-error cases. A separately named kernel,
`7.0.0-gemini-lk-clockrtc-chgstatus`, is building with matching modules and images.
Active or unreadable thermal alarms still use the original protection path.
Full hardware qualification is pending; see the
[charger investigation](charger-thermal-irq-2026-11-02.md).

## Bootloop recovery checkpoint at 05:58 WIB

After the user reconnected the phone in Fastboot, USB image transfer worked.
The previously verified diagnostic kernel RAM-booted successfully. The installed
boot prefix still matches `294e1958...`; no newer image has been installed.
The userdata filesystem mounted read-only with journal replay disabled.

The retained journal contains eight short boots. The last boot records
`HARDWARE PROTECTION shutdown (Charger thermal emergency)` followed by forced
shutdown. This identifies a shutdown path in the charger driver, not yet whether
there was real overtemperature or an incorrect driver/interrupt report. Source
review found `temp-shutdown` configured for both interrupt edges and a handler
that invokes hardware-protection shutdown without reading live charger status.
A deassertion-edge trigger is a hypothesis requiring verification, not an
established explanation. No protection was disabled and no fix has been flashed.

The journal archive was copied off the phone and its SHA-256 matched the source.
The phone was returned to responding Fastboot, keeping userdata intact and
avoiding repeated normal boots through the shutdown path. The remaining tests
and charger investigation need a new testing window after 06:00 WIB. See the
[recovery record](measurements/2026-11-02/bootloop-recovery.json).

## Completed evidence

- Full 26,856,108,032-byte userdata backup verified against the phone source,
  copied data and a final host reread; offline read-only ext4 check passed.
  A matching original boot recovery set is retained privately.
- Explicitly authorized backup-GPT CRC repair changed four bytes only; full-LUN
  readback matched. The first clean production boot had no GPT warning.
- The first generic clean install booted `7.0.0-gemini-lk-clockrtc #2`, completed
  Armbian onboarding, and provided authenticated root/user SSH over USB and
  Wi-Fi. English UTF-8 and Asia/Jakarta were configured. That initial check had
  zero kernel taint and no failed systemd units before stress fixtures ran.
- The host installer now streams flash progress, caps transfers at the smaller
  of 256 MiB and the bootloader limit, and requires fastboot 37.0.1 or newer.
  Its 21 preflight/failure tests passed; the full boot suite had 50 Python
  tests plus two native init safety modes. Service tests: 22; soak tests: 12.
- On the first installed kernel, corrected Docker tests passed hardening and
  cgroup configuration, bridge DNS/HTTP, retained state after restart, stopped
  application backup/restore, and continued HTTP service. SQLite WAL crash
  rollback and integrity passed. The copied SQLite backup passed an independent
  host integrity check with the expected 16 committed rows.

## Findings retained and current work

The initial two-worker CPU/RAM fixture stopped at its conservative 70 C guard:
74.8 C was sampled after about 25 seconds. A higher-frequency diagnostic also
stopped; it observed cooling states increasing near the 65 C passive trip, but
frequency reductions were gradual and the last sample reached 71.9 C. These
are stopped tests, not passes. The existing soak CPU acceptance ceiling is
85 C; neither observation alone proves failure of that separate criterion.
The proposed response raises the minimum cooling state at the existing trip
to 4 for the little cluster and 8 for the big cluster. Critical trips are
unchanged. This revision has not yet been tested or installed on the phone.

The earlier Docker client exit 139 came from this test's unsupported `wget -T`
option on Debian BusyBox. The help output does not list that option. Supported
requests without it passed by both container IP and name, and `nslookup`
passed. The failed commands and corrected controls remain retained. They do
not establish a Docker DNS or kernel regression; the invalid-option crash
mechanism itself has not been fully determined.

The generic image now removes USB serial root autologin so host modem probes
cannot enter an automatically logged-in root onboarding session. Static rootfs
and image checks passed. Actual first boot of that image revision is pending.
The laptop also has phone-specific ModemManager exclusions, including a
physical-port-specific rule for the diagnostic gadget; its cellular modem was
left unchanged.

The thermal rebuild first failed because the builder lacked ARM64 libc
headers. The dependency is now explicit in `setup-deps.sh` and installed in the
builder. A subsequent attempt found Ubuntu's packaged `mkbootimg` unable to
import its `gki` module. The build script now supports an explicit `MKBOOTIMG`
executable and checks it before rebuilding initramfs. A private copy of the
previously used host packager is selected for the current build. Its identity
and the failed logs are retained. The final rebuild exited successfully at 00:44 WIB. Both archive checks
passed, all 186 recorded product inputs match, and the three boot image hashes
and loose DTB match the new provenance. The production boot SHA-256 is
`bb8c480f546217ae8adbb9760f1df64771d2287ccd358df6a0f5edf2fef03326`;
this is not the boot currently installed on the phone. See the
[offline candidate identity](measurements/2026-11-02/offline-candidate.json).

Before the 05:58 recovery, both the revised diagnostic image and a
previously hardware-tested diagnostic image failed during USB download with
fastboot 37.0.1 and 34.0.5. USB reset restored small control commands, but a
software bootloader restart did not restore bulk downloads. The user's physical
USB reconnect subsequently restored transfer of the known diagnostic image.
These earlier failures remain recorded; they do not establish an image fault.

At the historical 08:19 WIB checkpoint the phone was running the old diagnostic kernel
from RAM, with internal storage read-only and no production rootfs mounted.
The LCD backlight is intentionally off to conserve power. The last battery
reading at 08:11 was 27%, with a 25 C battery temperature on laptop USB (SDP).
The separately named charger-status kernel is still compiling; its charger
driver object has compiled with the new status-handling paths. This proves
object compilation only, not successful full-image construction or runtime
behavior. No newer production image has been flashed since the first clean
installation.

## Remaining release gates

1. Fresh installation and onboarding of the policy-fixed final generic image
   have now passed, including package service autostart and restored app data.
2. Complete the remaining three USB boots and per-boot physical LCD checks
   for the final configuration; two USB boots have passed.
   Five consecutive DCP charger-runtime reboots already passed with persistent
   application data, filesystem checks, Wi-Fi SSH/HTTP and remote LCD cycles.
3. Current-runtime AP-return and repeated DHCP renewal checks have now passed.
   The user removed the 24-hour criterion after a paired short observation
   without failures; no full-duration reliability claim is made. Bounded CPU/RAM and application/storage
   tests already passed; preserve the earlier HTTP timeout and coverage gap.
4. The throughput criterion was explicitly revised by the user to minimum
   0.5 MB/s on the present 2.4 GHz Wi-Fi. Existing native measurements of
   0.652 and 0.588 MB/s meet it. This does not establish 24-hour sustained speed.
5. Keep Windows claims limited to the tested Windows 11 physical USB passthrough
   setup ; final-revision RNDIS/NCM retesting passed. Native Windows PCs, Windows 10 and
   full-system backup restoration remain unverified. Future LAN hardware remains
   outside the initial Wi-Fi scope.

No stable release, commit or GitHub publication has been made. Private phone
backups, credentials, configuration snapshots and detailed logs stay under
`out/`. The dated acceptance history remains available in
[the main report](stability-acceptance-2026-10-31.md).
