# Armbian for Xiaomi Mi 5 — documentation

The project, system console and SSH messages use English. See the
[language policy](language-policy.md) for locale settings and verification.

Current status, 3 November 2026: **0.1.0 is qualified for the targeted Wi-Fi
server scope.** See the [final stability report](stable-release-0.1.0.md) for
test coverage, version-only promotion and limits. This is a community port;
it does not establish uninterrupted 24/7 service or universal device support.

See [public source distribution](open-source-publication.md) for licensing,
local firmware inputs and the source-only GitHub release. SSH examples use root.

## Start here

| Document | Purpose |
|---|---|
| [0.1.0 stability report](stable-release-0.1.0.md) | Final qualification, evidence and untested scope |
| [Historical acceptance](stability-acceptance-2026-10-31.md) | Charger, DHCP, application backup/restore and measured soak results |
| [Filesystem recovery](filesystem-recovery-2026-10-30.md) | Completed ext4 repair, verified boot order and remaining limitations |
| [English language rollout](english-language-2026-10-30.md) | System/SSH change and validation |
| [October progress history](stability-progress-2026-10-30.md) | Changes, measured results and outstanding tests |
| [Post-install maintenance](server-maintenance-2026-11-03.md) | Security updates, Compose, log limits, SSH keys, firewall and laptop backup |
| [Stability plan](stability-plan.md) | Release criteria, diagnostics and recovery |
| [Flash guide](flash-guide.md) | Current prerequisites, diagnostics and installation |
| [First Wi-Fi](first-wifi.md) | First login, Wi-Fi and SSH through USB console |
| [Wi-Fi board data](wifi-board-data.md) | Required original firmware input and early-driver validation |
| [Docker server](docker-server.md) | Install Docker after onboarding and validate ARM64 applications |
| [LCD console](lcd-console.md) | Login console, brightness and display sleep |
| [USB management](usb-management.md) | Linux/Windows management paths and test scope |
| [Network policy](network-policy.md) | Wi-Fi primary, LAN backup and routing limitations |
| [Console/USB/charging worklog](console-usb-2026-10-30.md) | Hardware observations and open regressions |
| [Project metadata](../config/project.json) | Public identity and release version |

## October bring-up and audits

| Document | Purpose |
|---|---|
| [Original audit](audit-2026-10-29.md) | Defects in superseded artifacts |
| [LK memory audit](bootloader-memory-2026-10-29.md) | Effective addresses, ARM64 wrapper and validation |
| [Native progress](bringup-progress-2026-10-29.md) | Installation, Docker, thermal/power tests |
| [ADB recovery](adb-recovery-2026-10-29.md) | Read-only Android inspection and logging |
| [Reference server](reference-armbian-2026-10-29.md) | Armbian architecture/ABI findings |
| [Further hardware tests](next-hardware-test.md) | Diagnostic procedure and remaining hardware work |

## Historical August Linux/Ubuntu work

These records describe earlier kernels, boot headers, partitions and a graphical
HUD. They do not certify current Armbian packages or replace the current flash
guide. Header-only load assumptions were superseded by the October LK audit.

| Document | Topic |
|---|---|
| [What was built](what-we-built.md) | Historical HUD, Wi-Fi and boot chain |
| [Bring-up plan](bringup-plan-linux-7.0.md) | P0–P8 development stages |
| [First Linux 7.0 boot](linux-7.0-bringup.md) | Early failures and successful RAM boot |
| [Device inventory](device-inventory.md) | Historical hardware/partition map |
| [Display and reboot](display-and-reboot-fastboot-7.0.md) | XRGB scanout and direct reboot helper |
| [28 August worklog](worklog-2026-08-28.md) | Fuel gauge, Docker, Adreno |
| [29 August worklog](worklog-2026-08-29.md) | HUD Wi-Fi/password/forget flow |
| [30 August worklog](worklog-2026-08-30.md) | Panel blanking and touch recovery |
| [Upstream research](upstream-research.md) | DTS/driver differences recorded at the time |
| [Ubuntu live dump](hardware-dump-ubuntu.md) | Hardware evidence from the old installation |
| [GNOME](gnome-desktop.md) | Experimental overlay; GDM remains masked |
| [Reboot to LK](reboot-fastboot.md) | Legacy helper constraints |

UART pad map: [inventory notes](../inventory/uart-gemini/README.md).
