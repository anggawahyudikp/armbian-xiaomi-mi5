# Armbian for Xiaomi Mi 5

**Give your Xiaomi Mi 5 a second life as a Linux server.**

Community Armbian port for **Xiaomi Mi 5** (`gemini`, Snapdragon 820 / MSM8996),
using the stock LK bootloader and Debian Bookworm ARM64 userspace.

[Documentation](docs/README.md) · [Source releases](https://github.com/anggawahyudikp/armbian-xiaomi-mi5/releases) · [Contributing](CONTRIBUTING.md) · [Contributors](CONTRIBUTORS.md)

This project turns a Mi 5 into a small server with a **Linux console on its LCD**,
**Wi-Fi as the primary network**, and **USB network + serial management**.
The public repository name is `armbian-xiaomi-mi5`; hardware identifiers remain
`gemini` and `msm8996`. This is a community port, not official Armbian device support.

## First stable release

**Version 0.1.0 is our first stable release for lightweight, Wi-Fi-connected
server workloads.** It is the result of extensive hardware bring-up, repeated
real-device testing, and multiple rounds of debugging and refinement across
boot, charging, networking, storage, USB management, and display controls.

The project brings an ARM64 Linux server, Docker support, Wi-Fi connectivity,
and a working LCD console to the Snapdragon 820 platform. The release uses the
existing battery and normal USB charging, with Wi-Fi as its primary uplink.

**Tested on real hardware:** five consecutive USB reboots and five
charger-powered runtime reboots passed, alongside Docker persistence,
application backup and restore, Wi-Fi recovery, and bounded CPU/RAM testing.
Power and Home controls were physically verified after every final USB reboot.

See the [0.1.0 stability report](docs/stable-release-0.1.0.md) for the measured
results and validation scope. The [source release](docs/open-source-publication.md)
includes build configuration, host tests, and English documentation; prepare
local firmware inputs before building installation images.

## Use the device

The project, system console and SSH messages use English (`en_US.UTF-8`).
Client-forwarded locale settings do not change the SSH server language.

- **LCD:** Linux boot output and a normal login console. Display-only sleep
  defaults to five minutes. A short Power press toggles the display; Docker,
  Wi-Fi, SSH and CPU availability are independent of LCD sleep.
- **Wi-Fi:** the primary Internet connection, managed by NetworkManager.
- **USB:** local SSH at `192.168.7.2` and a serial console. DHCP supplies the
  computer with an address, without advertising a gateway or DNS server.
- **Power:** use a suitable charger for normal server operation. The battery
  bridges cable changes; laptop USB is a maintenance connection.

```sh
mi5-config status
mi5-config display timeout 300
mi5-config display brightness 20
mi5-config display wake
mi5-config display sleep
mi5-config usb status
```

Use `root` for Wi-Fi and USB SSH after completing Armbian first login and
setting your own root password. For USB: `ssh root@192.168.7.2`.
No personal username or password is built into the public image.
The generic image contains no personal Wi-Fi profile or SSH keys.
The public repository distributes source only. Device firmware and original
backups remain local; see [firmware inputs](docs/firmware-inputs.md).
Docker is installed separately after first login; see the
[Docker server guide](docs/docker-server.md).
See [first Wi-Fi setup](docs/first-wifi.md), [LCD console](docs/lcd-console.md),
and [USB management on Linux/Windows](docs/usb-management.md).

## Build

On Linux, install the dependencies listed in `scripts/setup-deps.sh`, including
an ARM64 cross-compiler and rootless Podman.

Boot image packing uses the [pinned standalone AOSP/Debian tool](scripts/vendor/README.md)
included in the repository. It avoids a missing `gki` Python module in some host
packages. `MKBOOTIMG=/path/to/executable` remains available for an explicit override.

First prepare the required [Mi 5 Wi-Fi board data](docs/wifi-board-data.md)
from the original modem firmware. The build rejects the old generic fallback.
Then run:

```sh
./scripts/build-all.sh
```

The Armbian framework revision is pinned in `armbian/framework-revision`.
The build checks the kernel, target ARM64 userspace, LK memory layout, filesystem
images and archive contents before reporting success. `OUT` defaults to
`out/validated`; `KBUILD_OUTPUT` can select an existing kernel build tree.

Project identity and release version come from [config/project.json](config/project.json).
For version 0.1.0, the main output files are:

| Artifact | Purpose |
|---|---|
| `armbian-xiaomi-mi5_0.1.0_fastboot.zip` | PC installer for Windows and Linux |
| `armbian-xiaomi-mi5_0.1.0_twrp.zip` | Recovery installer; device installation still needs testing |
| `boot.img` | Production boot image; requires an installed Gemini rootfs |
| `boot-diagnostic.img` | RAM-only diagnostic shell; leaves internal filesystems unmounted |
| `rootfs.ext4` / `rootfs.img` | Raw ext4 / Android sparse rootfs |
| `SHA256SUMS`, `build-provenance.json` | Artifact hashes, source identity and validation scope |

## Install and recovery

**Installation erases Android userdata and replaces boot.** Boot/recovery backups
do not include personal Android data. Read the [installation guide](docs/flash-guide.md)
first. The installer requires device identity and an audited aboot firmware hash;
these images are not interchangeable with other Snapdragon phones.

Do not use the old `Armbian-Mi5-Gemini-v24.11-*` or memory-overlapping artifacts.
Their problems are documented in the [29 October audit](docs/audit-2026-10-29.md).
August Linux/Ubuntu notes are historical records, not current release instructions.

## Checks

```sh
bash tests/boot/run.sh
python3 -m unittest discover -s tests/server
bash tests/wifi-flow/run.sh
```

Build validation and real hardware tests are reported separately. Publishing is
explicit: `scripts/publish-release.sh --prepare` generates release notes locally;
`--publish OWNER/REPO` publishes a prerelease only when intentionally requested.

[Stability criteria, diagnostics and outstanding hardware tests](docs/stability-plan.md)

## Validation and known limitations

Version 0.1.0 is stable for the tested lightweight Wi-Fi server scope described
above. Short transfers of 0.652 and 0.588 MB/s meet the user-revised minimum of
0.5 MB/s. The 24-hour acceptance gate was removed by the user; uninterrupted
24/7 service has not been established. One independent HTTP connection timeout
during load remains recorded in the stability report.

Linux USB RNDIS/NCM passed. Windows 11 was tested with the actual phone forwarded
to QEMU. Native Windows PCs, Windows 10, physical USB Ethernet/LAN failover,
TWRP installation, and full-system restoration remain untested.

The promotion to 0.1.0 changed version metadata only. Kernel, boot, and functional
rootfs contents match the hardware-tested candidate; an additional flash of the
metadata-only image is not claimed. Original backups and firmware inputs remain
private, and firmware-equipped binary images are not distributed here.

## Contributors and acknowledgments

- **[AnggaWekape](https://github.com/anggawahyudikp)** — project maintainer,
  hardware access, physical testing, and release decisions.
- **Google Gemini** — acknowledged AI development assistant.
- **OpenAI ChatGPT** — acknowledged AI development assistant.

Thank you to the Linux, Armbian, and device-support communities whose work makes
this port possible. See [CONTRIBUTORS.md](CONTRIBUTORS.md) for project credits
and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for licensing attribution.
