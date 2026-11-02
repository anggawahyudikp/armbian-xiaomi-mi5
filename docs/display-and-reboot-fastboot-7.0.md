# Display scanout and in-OS reboot-fastboot (2026-08-28)

> Historical August 2026 Linux/Ubuntu record. Current installation and load
> rules are in the [flash guide](flash-guide.md) and
> [LK memory audit](bootloader-memory-2026-10-29.md).

JDI R63452 command-mode panel, XRGB8888 fbdev. HUD owns `/dev/fb0` (or GBM/GLES2). GDM stays masked.

`display-unblank.service` must be **Type=simple** and stay running so Volume keys are heard. Short **Volume Up** (no Power) issues `SYS_reboot(..., "bootloader")`. Success is USB `18d1:d00d`. A black screen is not LK.

Do not start GDM from that oneshot. Do not type reboot into ACM.

## Historical scanout details

Recorded 28 August, before the current Armbian console. A RAM boot retained the
6.1 partition. JDI R63452 command-mode MSM fbdev exposed 1080×1920 XRGB8888.
At 19:24 a short Volume Up press through the running listener entered actual
LK USB `18d1:d00d`. Hardware Volume Down + Power after shutdown is a separate
path and does not validate Linux userspace reboot.

| Visual result | Interpretation from those tests |
|---|---|
| Backlight on, black | Black scanout buffer or GDM/X replacing the framebuffer |
| Top purple, bottom black | RGB565-sized write into a 32-bit buffer; only half filled |
| Full purple | Repeated 0xE007 pattern across the full 4-byte buffer |
| Full green | Little-endian B,G,R,X bytes 00,FF,00,00 |
| Green with yellow bottom stripe | Listener alive; yellow bytes 00,FF,FF,00 in the bottom 240 lines |

The userspace probe loaded panel/MSM modules, waited for DRM/fb0, painted the
probe and listened for Volume/Home/touch events. `Type=simple` kept that listener
alive; a oneshot starting GDM could lose input handling and overwrite scanout.
Logs were `/var/log/gemini-display.log` and `/var/log/reboot-fastboot.log`.

Do not guess RGB565, start GDM over a verified scanout, or treat a FASTBOOT splash
as evidence of bootloader mode. In these experiments the helper used direct
RESTART2 `bootloader` through PM8994 PON to avoid a stalled DRM shutdown. Avoid
PSHOLD/IMEM accesses that previously hung this phone. See
[reboot constraints](reboot-fastboot.md) and the later
[blanking worklog](worklog-2026-08-30.md).

Historical headers used base0x80000000, kernel0x80008000 and ramdisk0x84000000.
They are superseded for current builds by the
[effective-LK memory audit](bootloader-memory-2026-10-29.md).
