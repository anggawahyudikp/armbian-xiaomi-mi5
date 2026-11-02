# First Wi-Fi connection on an installed Mi 5

Use the USB console from a computer for initial setup. Neither Wi-Fi nor LAN is
required to open it. Authenticated USB console access, generic first-login onboarding, Wi-Fi
association and SSH have worked on this Mi 5. The manual `nmcli --ask` procedure
below is for the generic image, which contains no personal Wi-Fi profile.
Run these steps in the installed Armbian system, after hardware tests and
installation; they do not apply to Android or the diagnostic initramfs shell.

1. Connect a USB data cable. Identify the Mi 5 ACM port through
   `/dev/serial/by-path/` or `udevadm`. The legacy serial gadget uses
   `0525:a4a7`; the current composite gadget also provides ACM. Do not assume
   `ttyACM0`: ACM0 through ACM2 on the audited laptop belong to a Lenovo modem.
2. Open the verified port at 115200 baud, 8N1, with flow control disabled.
   Replace the example port name:

   ```bash
   screen /dev/ttyACM_MI5 115200
   ```

   Exit screen with `Ctrl+A`, then `K`, then confirm. Open only one terminal on
   the Mi 5 serial port.
3. Press Enter after opening the terminal. The console waits for a carriage
   return before displaying its prompt. Log in as `root` with the image's initial
   password `1234`, then complete Armbian's mandatory password change and user
   creation. Serial autologin is disabled from the first boot. Use the wireless
   setup prompt if offered. If skipped or unsuccessful, continue below.

Run these commands **on the Mi 5 Armbian console** as root. Add `sudo` to commands
that change configuration when using a regular account:

```bash
nmcli device status
nmcli radio wifi on
nmcli device wifi list
nmcli --ask device wifi connect "YOUR_WIFI_SSID" name mi5-wifi
nmcli connection modify mi5-wifi connection.autoconnect yes
```

Enter the password at the `--ask` prompt instead of placing it on the command
line. NetworkManager saves the profile for future connections. If onboarding
already connected Wi-Fi, do not create a second profile with these commands.

Check the address and routing:

```bash
nmcli -f GENERAL.DEVICE,GENERAL.STATE,IP4.ADDRESS,IP4.GATEWAY device show
ip -4 route show default
getent hosts deb.debian.org
```

Once Wi-Fi has an address, connect from a computer that can reach that network:
`ssh root@MI5_WIFI_IP`. Use the root password you set during first login. SSH host keys are unique to each installation; the generic image does not
ship the builder's private keys or Wi-Fi credentials.

New Wi-Fi profiles use a locally generated stable MAC address because the
board firmware contains a shared template address. It remains stable for that
installation and profile; set router DHCP reservations after first connection.
An explicitly configured profile MAC takes precedence.

Wi-Fi route metric defaults to 100 and LAN to 600 for IPv4/IPv6. Creating a
Wi-Fi profile does not require changing those defaults. Physical LAN backup
still needs USB host, adapter and power testing; see [network policy](network-policy.md).

If `nmcli device status` shows no Wi-Fi device, entering a password cannot fix
that. Collect `iw dev`, `rfkill list` and `dmesg` to inspect PCIe/QCA6174/firmware.
Keep using USB for recovery until another path has actually been verified.

This procedure follows the authenticated `serial-getty@ttyGS0` unit and
`armbian-firstlogin` in the pinned framework. Command syntax
follows the [NetworkManager 1.42.4 examples](https://networkmanager.dev/docs/api/1.42.4/nmcli-examples.html).
