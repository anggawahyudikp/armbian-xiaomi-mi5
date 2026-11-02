# Reboot to LK from Ubuntu

## Verified orderly software entry (2026-11-01)

On the running Mi 5 kernel, `systemctl reboot bootloader` successfully entered
Fastboot without Volume Down held. The test checked the input-key state before
the request, USB `18d1:d00d`, matching device serial and a successful
`getvar product` response (`MSM8996`). The bootloader reported an unlocked device
and a 512 MiB maximum download size. This is one successful entry on that
revision; the separate clock/RTC candidate still needs its own hardware test.

Use the orderly systemd request on this verified installed system. The host
helper below still prefers the legacy direct-reboot executable, so it does not
yet implement this newly verified route. Earlier direct-entry failures remain
historical evidence and do not establish that orderly entry is impossible.

## Current Linux host helper

`scripts/reboot-fastboot.sh` verifies USB `18d1:d00d`, chooses a device serial,
and requires a bounded `getvar product` response before reporting readiness.
Text from `fastboot devices` alone is insufficient: a composite Linux gadget
produced misleading output during the October tests. Set `PHONE_SERIAL` when
more than one bootloader is connected.

The SSH path requires an already verified host key and noninteractive SSH
authentication. Set `PHONE_IP` and `SSH_USER` for the existing management
connection. Unknown or changed SSH keys are rejected.

The earlier October test accepted the direct bootloader reboot request but
returned to Linux. That direct-helper route remains unverified; physical
Volume Down + Power is a verified fallback. The host helper does not flash
partitions or treat a failed readiness check as a successful bootloader entry.

## Historical implementation

> Historical August 2026 Linux/Ubuntu record. Current installation and load
> rules are in the [flash guide](flash-guide.md) and
> [LK memory audit](bootloader-memory-2026-10-29.md).

On the HUD: short **Volume Up** only. Do not hold Power (that combo is the hardware key for LK after shutdown).

From a shell: `reboot-fastboot` (static helper) or `sudo reboot bootloader`. Success is USB `18d1:d00d`.

Do not paste that command into the USB serial console; it races getty and can blank the panel while the OS is still running. Host helper: `./scripts/reboot-fastboot.sh` (set `PHONE_IP` if you use Wi-Fi SSH).

## Historical implementation constraints

The direct helper issues `SYS_reboot` / `LINUX_REBOOT_CMD_RESTART2` with
`bootloader`, bypassing systemd shutdown in the old Ubuntu HUD experiment
because DRM shutdown could stall before reset. PM8994 PON mode-bootloader was
`0x2`. This is a distinct legacy recovery path from a normal orderly server
reboot.

Adding ginkgo-style pshold at `0x4ab000` or mapping MSM8996 IMEM, either through
boot syscon or `/dev/mem` at reset, hung this phone. Do not reintroduce either
as an assumed fix. The old umeko passwordless helper depended on correctly
owned root:root sudoers files and a 0755 sudoers directory; it is not a shared
credential policy for new installations.

After power-off, Volume Down + Power enters LK; Power + Volume Up enters TWRP.
Only USB `18d1:d00d` establishes LK fastboot. A black screen, FASTBOOT splash
or an unchanged `0525:a4a7` gadget does not. Keep working boot backups and use
current [LK layout checks](bootloader-memory-2026-10-29.md) for new images.
