# Optional post-install server maintenance

These examples describe the maintenance setup tested on the installed Mi 5.
They are opt-in post-install components, not defaults in the 0.1.0 generic
image. Read the [execution report](../../docs/server-maintenance-2026-11-03.md)
for measured results and limits. Review paths and trusted networks before use.

## Components

| File | Purpose |
| --- | --- |
| 20mi5-periodic and 52mi5-security-upgrades | Debian Bookworm security-only automatic updates, with hardware-sensitive packages excluded and automatic reboot disabled |
| mi5-docker-compose.pref | Permit only the Compose plugin from Docker's official APT repository; keep the current Engine package source |
| docker-daemon-logging.json | Logging keys to merge into the existing Docker daemon configuration |
| mi5-server-firewall.sh, .service and .default | Private-network host and Docker forwarding policy using existing iptables/ip6tables |
| mi5-backup-export.py | Root-only streaming export of system configuration, Compose definitions and prepared application exports |
| mi5-backup.py | Laptop-side SSH pull, archive validation, atomic publication and fourteen-snapshot retention |
| mi5-backup.service and .timer | Laptop user units for a daily pull around 03:30 local time |

## Phone prerequisites and installation

Use the Bookworm-based Mi 5 image, Python 3.11+, Docker, iptables/ip6tables and
root access. The Compose plugin setup uses the repository/key section of
[Docker's Debian instructions](https://docs.docker.com/engine/install/debian/)
and the supplied pin file. Check the proposed APT transaction before installing
the plugin. On the tested phone only the plugin was added; Engine was retained.

Merge the logging keys with existing daemon.json content. A Docker restart
applies defaults to newly created containers. Plan for running applications
before restarting or recreating containers.

For the export helper, run as root from a source checkout:

```sh
install -m750 examples/server-maintenance/mi5-backup-export.py /usr/local/sbin/mi5-backup-export
install -d -m700 /opt/stacks /var/backups/mi5-apps
```

The firewall example allows host TCP 22 from configured private ranges, required
DHCP/ICMP traffic, and private-source Docker publishing. Review its .default
file and preserve a verified recovery connection and timed rollback before
applying it. It is intended for the documented private Wi-Fi/USB server scope;
public endpoints and other routing roles require a reviewed policy.

## Linux laptop backup

Use a Linux laptop with a systemd user manager. Configure an SSH alias named mi5-armbian pointing to your phone, with User root,
your own private key, and a verified host-key pin. Verify BatchMode SSH works
before enabling the timer. The repository supplies no keys or passwords.

```sh
install -d -m700 ~/.local/bin ~/mi5-backups
install -m700 examples/server-maintenance/mi5-backup.py ~/.local/bin/mi5-backup
install -d -m755 ~/.config/systemd/user
install -m644 examples/server-maintenance/mi5-backup.service examples/server-maintenance/mi5-backup.timer ~/.config/systemd/user/
~/.local/bin/mi5-backup
systemctl --user daemon-reload
systemctl --user enable --now mi5-backup.timer
```

The timer runs while the laptop user manager is available; Persistent=true
catches a missed calendar run when it becomes available again. The source SSH
alias must remain reachable. Existing backups are retained if a pull fails.

Archives contain system secrets and are not encrypted by these examples.
Keep the private backup directory outside Git and public storage. The export
covers /etc, root authorized keys, /opt/stacks and prepared exports in
/var/backups/mi5-apps. It does not copy live Docker volumes or full userdata.
Use the database's consistent dump/export mechanism for application data,
then verify restoration separately before treating that data as backed up.
