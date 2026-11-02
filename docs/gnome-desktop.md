# GNOME on gemini

> Historical August 2026 Linux/Ubuntu record. Current installation and load
> rules are in the [flash guide](flash-guide.md) and
> [LK memory audit](bootloader-memory-2026-10-29.md).

Overlay prepares GDM autologin, Wayland, modesetting+glamor, scale 2, on-screen keyboard, no idle lock. **GDM stays masked** while the HUD owns MSM scanout; unmasking it blacks the panel.

This is not the default UI. Flash/boot still starts `display-unblank` → `gemini-status`.

## Historical setup, not the Armbian server default

The original Ubuntu 20.04 rootfs had KlipperScreen, not gdm3/gnome-shell. The
legacy overlay targeted autologin `umeko`, Wayland, modesetting/glamor, scaling
2 and an on-screen keyboard with no idle lock. It masked KlipperScreen and
xwayland_ks. A first-boot service waited for networking and installed
ubuntu-desktop-minimal from the configured ubuntu-ports mirror, approximately
1–2 GB, logging to `/var/log/gemini-gnome-setup.log`.

Those experiments deployed the overlay during switch_root or through TWRP
using `scripts/push-gnome-via-recovery.sh`. They did not require formatting the
existing Ubuntu userdata. GNOME could take MSM scanout to black, so GDM remains
masked in the server profile. If revisiting composition, inspect gdm logs for
`egl: failed to create dri2 screen`; the historical target was Mesa msm/
freedreno on Adreno 530 at 1080×1920, scale 2. Current build/install instructions
are in the [flash guide](flash-guide.md), not these legacy procedures.
