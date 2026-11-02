# Armbian for Xiaomi Mi 5 — 0.1.0 stability report

Assessment: **0.1.0 qualified for the targeted Wi-Fi server scope below.** Hardware acceptance, metadata-only promotion, offline package validation and cleanup are complete. This is a community qualification; GitHub publication was a separate step after qualification.

The target is a lightweight Docker server using the existing battery, normal USB charging, Wi-Fi as the uplink, and an LCD Linux console with display-only sleep. LAN adapters and direct battery power modifications are future work.

## Acceptance evidence

| Check | Result and scope |
| --- | --- |
| Generic installation | Clean userdata installation, normal English-language onboarding and account creation passed. Docker/containerd started from package post-install scripts. |
| USB boot | Five consecutive reboots passed, with distinct boot IDs, boot continuity, working Wi-Fi SSH/HTTP, persistent counters and unchanged host default routes. Readiness: 67.63, 53.58, 65.22, 54.79 and 94.86 seconds. |
| Charger boot | Five consecutive DCP-source runtime reboots passed in 59.49–61.02 seconds, with battery increasing from 65% to 68%. The kernel and selected functional userspace matched the release candidate. |
| LCD | Operator confirmed Power sleep/wake, Home wake and visible Linux after all five USB boots. Remote backlight-zero/wake checks passed. Earlier native physical input traces are retained; the later capture windows missed the operator actions, so those rounds rely on operator confirmation. Display sleep does not suspend the server. |
| Wi-Fi recovery | Eleven matching DHCP REQUEST/ACK renewals over ten minutes; a controlled 35-second AP outage recovered HTTP automatically about ten seconds after AP return, without reboot or data loss. |
| Throughput | Short transfers measured 0.652 and 0.588 MB/s, meeting the user-revised minimum of 0.5 MB/s. This is not a guaranteed future link speed. |
| Docker and storage | Six app/storage checks passed, including container restrictions, bridge networking, persisted restart state, consistent app backup/restore and SQLite WAL crash recovery/integrity. |
| CPU/RAM | Two 128 MiB workers passed a bounded five-minute run. Maximum observed CPU temperature was 71.6°C; battery 25.5°C. One independent HTTP connect timeout during load remains in the record; no zero-interruption guarantee is claimed. |
| USB maintenance | Linux RNDIS/NCM network, SSH and serial passed. The actual phone passed RNDIS/NCM class-driver, DHCP, SSH/PTY, HTTP and serial checks in Windows 11 build 26300.9457 under QEMU, preserving the controlled default route. |
| Clock and boot diagnostics | Kernel taint and ext4 error counts were zero; no failed services or fatal kernel messages in final checks. NTP synchronized after reboot. Saved software time is enabled, including orderly-shutdown and hourly saves. The raw PMIC RTC is not accurate offline UTC. |
| Recovery material | Original full userdata and matched boot backups were checksum-verified. Final consistent app/config/diagnostic snapshot was copied off-device and verified before cleanup. Full-system restoration on hardware remains untested. |

## Release identity and promotion

The tested functional candidate was named `0.1.0-preview.1`. Promotion to `0.1.0` changes only the version field in `config/project.json` and `/usr/share/mi5/project.json`. A comparison of 49,677 generic rootfs entries verified that all other contents, modes, owners and extended attributes are identical. Boot, kernel and DTB hashes are unchanged. The running Mi 5 received the same metadata update.

The stable ext4/sparse images and installer archives are rebuilt and independently validated. A new full flash of these metadata-only images is not claimed: first-boot and runtime evidence come from the functionally identical generic predecessor. Exact artifact hashes and evidence checksums are recorded in the machine-readable qualification report.

## Cleanup and current phone

The temporary application, test network, workload unit and test-specific battery guard were removed after testing and verified off-device backup. SSH, NetworkManager, Docker, containerd, USB gadget, console and the production health timer remain active. No user service was disabled, no phone shutdown was scheduled, and the qualification step did not publish GitHub content.

Final observed battery was 77%, battery temperature 25°C, CPU maximum 47.5°C. The system uses English locale. Wi-Fi conditions can change with distance and interference.

## Limits

The user removed the 24-hour acceptance gate; the retained approximately 28-minute paired observation is not a 24-hour pass. This qualification covers the targeted checks above, not uninterrupted 24/7 service or every workload.

Native Windows PCs, Windows 10, physical USB Ethernet/LAN failover, direct battery power, TWRP installation and full-system restoration have not been hardware-validated. Charger protection remains enabled; the asserted/read-error paths passed the callback harness, but a thermal emergency was not deliberately induced on the phone. The earlier shutdown regression did not recur during the documented charger and USB boot series; that does not prove its physical cause under all conditions.

Private original backups, credentials, Wi-Fi profiles and full diagnostic histories remain under ignored local output paths and must not be published.

[Machine-readable qualification](measurements/2026-11-03/stable-0.1.0.json) records artifact identity, evidence checksums and the exact scope of reused tests.
