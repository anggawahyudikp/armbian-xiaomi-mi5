# Post-install server maintenance — 3 November 2026

The existing Mi 5 received the optional maintenance configuration below after
its 0.1.0 hardware qualification. This did not rebuild the generic image,
change its version, upgrade Docker Engine, or modify the custom kernel/BSP.
The [reusable examples](../examples/server-maintenance/README.md) contain the
scripts and configuration, without credentials or phone-specific addresses.

## Completed changes

| Area | Installed configuration and verification |
| --- | --- |
| Security updates | Seven Debian security packages updated: libbrotli1, libexpat1, libsasl2-2, libsasl2-modules-db, libssl3, openssl, and tzdata. Package-manager audit was clean. |
| Automatic updates | Daily Bookworm security updates only. Automatic reboot disabled. Kernel, Armbian BSP, firmware, boot tooling, Docker/container runtime, and NetworkManager updates require manual review. The unattended-upgrades dry run passed and excluded unrelated Armbian candidates. |
| Compose | Official signed docker-compose-plugin 5.7.0 installed. The Docker repository is pinned to permit this plugin only. Existing Docker Engine 20.10.24 remains installed. A small local-image Compose service passed creation, HTTP access, restart, and recovery after Docker restart. |
| Logging | Docker local logging, maximum 10 MiB per file and three files per container. A newly created container inherited the exact settings. Existing containers would need recreation to adopt changed defaults; none remain on this phone. |
| SSH | Root key authentication verified through Wi-Fi and USB. Existing password authentication retained and tested as a fallback. Private keys and passwords remain local. |
| Firewall | Host SSH allowed from configured private networks, plus required DHCP/ICMP traffic. Docker-published services are limited to trusted private sources while Docker's own forwarding rules remain in place. Seven real packet-filter checks passed through temporary network namespaces, including blocked untrusted IPv4/IPv6 traffic and allowed private traffic. No physical LAN adapter was tested. |
| Backup | Laptop user timer scheduled around 03:30 local time, with up to ten minutes random delay; fourteen successful snapshots retained. Missed schedules catch up when the user timer becomes available. Successful off-device archives passed gzip integrity and SHA-256 verification. Two configuration files were restored into a temporary laptop directory and matched the phone. |

The firewall remained active after Docker restart and an orderly phone reboot.
The phone returned in about 45 seconds, with root key SSH, production services,
Compose availability, and logging configuration intact. Battery was 75% at
25°C. No failed units, kernel taint, or remaining test containers were observed.

## Daily use on the configured laptop

```sh
ssh mi5-armbian
ssh mi5-armbian-usb
systemctl --user list-timers mi5-backup.timer
systemctl --user start mi5-backup.service
cat ~/mi5-backups/latest.json
```

The SSH aliases are local laptop configuration and log in as root. Update their
HostName if DHCP assigns a different Wi-Fi address; a router DHCP reservation
can keep the address predictable. Root password access remains available.

Backups are private, unencrypted local archives under ~/mi5-backups on the
laptop, with directory mode 0700 and archive mode 0600. They include system
configuration, root SSH configuration, Compose definitions under /opt/stacks,
and prepared application exports under /var/backups/mi5-apps. Archives contain
secrets and must stay outside the public repository.

There are no deployed applications yet. This backup does not copy live Docker
volumes or full userdata. When deploying a database, add its consistent export
to /var/backups/mi5-apps before the scheduled pull. Application data is only
covered after that export is configured and a restore is verified. The laptop
must have an available user session and network access for the pull to run.

## Operational scope

The firewall defaults trust RFC1918 IPv4 ranges and ULA/link-local IPv6. Review
/etc/default/mi5-server-firewall before adding host services, global IPv6 access,
or VPN ranges. Test from a second connection with a rollback path when changing
access rules. Changing or restarting Docker reapplies this profile.

The security policy intentionally separates ordinary userspace maintenance
from hardware-sensitive updates. Excluded components, including the existing
Docker Engine and custom kernel, still require manual security review and
regression testing. This setup is not a claim that every installed component
is current or free of vulnerabilities.

All temporary test containers, networks, and namespaces were removed. The
original 0.1.0 qualification and its limits remain documented separately.
