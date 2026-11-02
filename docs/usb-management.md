# USB management on Linux and Windows

Connect the Mi 5 to a computer using a data cable. The composite gadget provides
one network adapter and one CDC ACM serial port. The phone address defaults to
`192.168.7.2/24`; DHCP gives the computer an address in the same subnet.

```sh
ssh root@192.168.7.2
```

Use the root password set during onboarding, or your own root SSH key, on both
USB and Wi-Fi. No shared personal password is distributed. Check the SSH host-key
fingerprint against the established Wi-Fi connection when connecting through
USB for the first time. Serial console login uses the same system accounts.

On Linux, identify the new network interface using `ip -brief address`; the
serial port appears under `/dev/serial/by-id/` or `/dev/serial/by-path/`.
On Windows, check Network Adapters and Ports (COM & LPT) in Device Manager.
Use an SSH client for the IP connection and a serial terminal for the COM port.
If the computer does not use DHCP, configure a free `192.168.7.x/24` address
(e.g. `192.168.7.1`) without a gateway or DNS server.

The USB DHCP service is limited to `usb0`, provides no DNS service, and suppresses
router/DNS options. It does not replace the computer's Internet connection or
the phone's Wi-Fi default route. USB is a local maintenance cable, not a physical
RJ45 LAN adapter or an Internet-sharing service.

## Host compatibility modes

| Mode | Target hosts |
|---|---|
| `rndis` (default) | Linux; Windows 10/11 using RNDIS and ACM drivers |
| `ncm` (optional) | Linux; Windows 11 using its NCM and ACM drivers |

```sh
sudo mi5-config usb status
sudo mi5-config usb mode ncm
sudo mi5-config usb mode rndis
```

Switch modes over Wi-Fi: USB disconnects and enumerates again. Linux supports
the configured gadget functions. Microsoft's
[class-driver table](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/supported-usb-classes)
lists ACM/RNDIS for Windows 10/11 and built-in NCM for Windows 11. Microsoft
recommends NCM for new devices; RNDIS remains the compatibility default here
because Windows 10 is in scope. Windows hardware results are recorded separately;
correct descriptors are not a substitute for a real Windows test.

The gadget includes Microsoft OS descriptors in RNDIS mode. Serial and MAC
addresses derive from the generated machine-id and remain stable per device.
No factory identity or shared fixed MAC is embedded in public images.

RNDIS uses device revision `0x0102`; NCM uses `0x0103`. Windows caches Microsoft
OS-descriptor discovery by vendor ID, product ID and revision, including a
negative result. Giving the modes separate revisions prevents NCM's absent OS
string from suppressing later RNDIS discovery. Both revisions also avoid the
old shared `0x0101` cache. See Microsoft's
[OS-descriptor cache documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/microsoft-defined-usb-descriptors).
Both corrected modes passed a physical Mi 5 USB passthrough test with Windows
11 Enterprise Evaluation build 26300.9457 in QEMU. NCM was tested before RNDIS
in the same guest; Microsoft class drivers, DHCP, SSH with a terminal, serial
login prompts and preservation of a controlled default route passed. See the
[dated hardware report](stability-acceptance-2026-10-31.md#windows-11-usb-validation-2026-11-01).
Native Windows PCs and Windows 10 remain untested.

`mi5-usb-gadget` owns the UDC. It stops the serial getty, unbinds built-in
`g_serial`, creates network+ACM, then restarts the getty. On failure it removes
its partial configuration and restores the legacy serial binding.
`mi5-usb-dhcp` runs as its own system account with only the capabilities needed
for local DHCP. The obsolete `usb-gadget-rndis.service` is masked.

Normal server operation uses a charger. Laptop USB may discharge the battery
under load; that is accepted for maintenance. Recheck charging after reconnecting
the charger. The battery bridges cable changes without stopping the OS.
