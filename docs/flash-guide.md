# Xiaomi Mi 5 installation and RAM diagnostics

Version 0.1.0 passed the targeted Wi-Fi server qualification. See the
[final stability report](stable-release-0.1.0.md) for metadata-only promotion,
retained failures and untested paths. The public GitHub release distributes
source only; build your images using the required local firmware inputs.
Installation erases Android userdata.

The installed aboot was subsequently found to override load addresses and make
the previous Linux images overlap DTB/ramdisk memory. Those boot images and ZIPs
are archived under `out/incompatible-stock-lk-2026-10-29/` and must not be used.
The replacement build uses the audited LK layout and an ARM64 alignment wrapper;
see the [bootloader memory audit](bootloader-memory-2026-10-29.md).

The old `out/Armbian-Mi5-Gemini-v24.11-*` packages failed the
[29 October audit](audit-2026-10-29.md). Use the build pipeline described in the
[project README](../README.md); new output goes to `out/validated/`.

## Backup and RAM diagnostics

While rooted Android is running, `python3 scripts/backup-device.py` backs up and
verifies the existing boot and recovery partitions. Back up personal Android
data separately: the helper does not copy userdata.

Arrange physical access to the Power button before a test. A kernel that hangs
before USB enumeration cannot be reset through ADB or fastboot.

After the diagnostic image passes its static checks and the bootloader is
confirmed unlocked, the RAM test command is:

```bash
fastboot boot out/validated/boot-diagnostic.img
```

This diagnostic initramfs does not mount userdata. It provides a USB ACM shell
and marks detected internal block devices read-only. Run `gemini-diagnostics`
from the serial terminal and save its output. `fastboot boot` returning OKAY
only confirms transfer/boot command acceptance; it does not prove Linux booted.

Production `boot.img` selects an installed Gemini rootfs and hands it to systemd
read-only for filesystem checking, followed by a normal writable remount.
It must not be described as a read-only live test for an Android installation.

## Permanent installation, after hardware validation

Installation erases all Android userdata and replaces `boot`. It preserves
recovery, bootloader, modem and the existing GPT. Have a verified recovery path
and personal backup before proceeding.

The generated Fastboot package is
`out/validated/armbian-xiaomi-mi5_0.1.0_fastboot.zip`. It requires Python
3.11+, Android SDK Platform-Tools fastboot 37.0.1 or newer, an unlocked bootloader, and exactly one connected
device. Extract the package, then run `flash-all.sh` on Linux/macOS or
`flash-all.bat` on Windows. The installer checks both payloads, checksums,
device identity, unlock state, partition sizes and the bootloader's reported
download limit before the first write. Transfers are capped at the smaller
of 256 MiB and that limit. Flash progress is displayed as it arrives. The boot payload must fit a raw download; an unknown
or inadequate limit aborts before either partition is written. Installation
requires an explicit erase confirmation.

On 1 November, fastboot 34.0.5 stalled twice during sparse userdata transfer
(with 64 MiB and 256 MiB caps). Google's fastboot 37.0.1 completed the same
image installation using 256 MiB transfers. The installer now checks the client
version before any writes. This identifies a tested installation combination;
the exact cause of the older client's stalls remains unresolved.

Supply `--device-proof <backup-directory>/metadata.json` for every Fastboot
installation. Run the current backup helper in rooted Android first. Proof must
identify `gemini`, match the fastboot serial and match the supported aboot hash;
the image's effective load addresses are firmware-specific. Some Mi 5 bootloaders
report `MSM8996`; that product name alone is insufficient. TWRP checks the
installed aboot hash itself before formatting.

The generated TWRP package is
`out/validated/armbian-xiaomi-mi5_0.1.0_twrp.zip`. Its recovery installer
stages and verifies both payloads in RAM before formatting userdata. Actual
recovery compatibility and available staging memory remain to be tested.
The current payload requires about 1.59 GiB of staging space before recovery
overhead; the exact current byte count is in `release-validation.json`.
Check actual free space in the recovery's
`/tmp`; this path has not been validated on the examined 3 GB Mi 5.

## First login

Open the verified phone ACM port at 115200 baud, 8N1, with flow control disabled.
Press Enter after opening it; the console waits for a carriage return before
showing the login prompt. The USB serial console requires a username and
password from its first boot.
Use the image's initial Armbian login (`root`, initial password `1234`) and
complete the mandatory password-change and user-creation flow. Use the new
root password for subsequent SSH access as `root`; the additional account
created by onboarding does not change that login choice. The LCD offers
local first-login onboarding. This prevents host modem probes from entering an
automatically logged-in root setup session over USB.

On Linux hosts running ModemManager, the optional local udev rules below
exclude only this Mi 5 gadget. Save them in
`/etc/udev/rules.d/78-mi5-console.rules`, run
`sudo udevadm control --reload-rules`, then reconnect the phone:

```udev
SUBSYSTEM=="usb", ATTR{idVendor}=="1d6b", ATTR{idProduct}=="010[45]", ATTR{manufacturer}=="Armbian community", ATTR{product}=="Armbian for Xiaomi Mi 5", ENV{ID_MM_DEVICE_IGNORE}="1"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1d6b", ATTRS{idProduct}=="010[45]", ATTRS{manufacturer}=="Armbian community", ATTRS{product}=="Armbian for Xiaomi Mi 5", ENV{ID_MM_PORT_IGNORE}="1"
```


The new image uses Armbian's first-login flow for password changes and user
creation. It does not pre-create the old `armbian` account with passwordless
sudo. SSH host keys are generated per device at first boot.

For first Wi-Fi setup through the USB serial console, see the
[first Wi-Fi guide](first-wifi.md). It covers identifying the
correct ACM port, Armbian onboarding, `nmcli --ask`, autoconnect and SSH.

`armbian-config` comes from Armbian's package. The separate `mi5-config` tool
provides local device helpers. Charge limiting, USB host/Ethernet, display and
network stability still require hardware tests; the old battery guard is masked.
