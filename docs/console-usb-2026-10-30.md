# Mi 5 LCD, USB and charging report — 30 October 2026

**Status: development preview. Kernel #6 is accessible over USB; charger-only
restart and reliable Wi-Fi have not passed final hardware testing.**

The implemented design provides an STB-like Linux LCD console, a five-minute
display idle timeout, primary Wi-Fi and USB network/serial management for Linux
and Windows. A charger is the normal power source. Battery discharge on laptop
USB is accepted for maintenance.

## Implemented changes

- The user physically confirmed a logo followed by Linux boot/login text after
  reset. MSM's `FBINFO_VIRTFB` was corrected so fbcon can draw. Display sleep
  disables the backlight; it does not suspend Linux or fully power down DSI.
- `mi5-console` defaults to 300 seconds, 20% brightness and short Power presses
  for display sleep/wake. Logind ignores Power as a system shutdown request.
- Composite USB supplies RNDIS or NCM plus ACM serial. The phone uses
  `192.168.7.2/24`; DHCP advertises neither a gateway nor DNS to the computer.
- `mi5-config` manages LCD, USB and Wi-Fi. Public identity is **Armbian for
  Xiaomi Mi 5**, slug `armbian-xiaomi-mi5`, version `0.1.0-preview.1`.
- A bounded, identity-checked PCIe enumeration helper runs before NetworkManager
  for late QCA6174 endpoints. It does not restart active connections.
- System shutdown leaves USB bound for kernel shutdown instead of rebinding
  gadgets/restarting getty. Ordinary mode changes still restore serial.

## Hardware tests before the charging-kernel update

| Check | Result |
|---|---|
| LCD boot/login | Physically confirmed by the user |
| Display sleep | Brightness zero; four CPUs and networking remained active |
| Docker during sleep | HTTP over USB/Wi-Fi and outbound HTTPS worked |
| Linux RNDIS | `rndis_host`, DHCP and SSH worked |
| Linux NCM | `cdc_ncm`, DHCP and regular-user SSH worked |
| ACM serial | Linux login prompt readable from the laptop |
| Laptop Internet route | USB DHCP did not replace it |
| Laptop-USB reboot | USB SSH returned; serial reached `Restarting system` |
| Charger-only reboot | Wi-Fi/SSH returned in about 62 seconds; Docker worked |
| Physical Power | Not yet confirmed at this stage; handler events tested offline |
| Windows | Not physically tested |

Initially the PCIe root port existed but the Wi-Fi endpoint was missing. One
PCI rescan restored it and Wi-Fi. Two subsequent boots worked without rescans;
that does not establish recovery across every cold/warm boot condition.

## Charging findings and subsequent tests

After a charger reboot, DCP, a 3 A limit and `online=1` were reported while the
battery was actually **Discharging**. Capacity fell 35% → 31%, with approximately
0.87–0.97 A discharge. Port presence and a configured limit do not prove charging.

Source tracing showed DWC3 can request 0 mA when a gadget is detached. SMBCHG
interprets a below-minimum request as USB input suspension. Recovery results
were consistent with that path, but the original callback sequence was not
captured in a kernel trace. Re-enabling the standard `online` property on DCP
immediately produced **Charging/Fast**, battery current approximately
**−1.4 to −1.55 A**, and capacity rose to 32%. Negative current means charging
for this driver.

The kernel fix leaves DCP/CDP AICL negotiation to SMBCHG and retains gadget
limits for SDP/laptops. The actual callback was tested against mocked DCP, CDP,
SDP, Unknown and port-type read failures. At this stage all 12 server tests,
83 required kernel settings and LK memory checks passed.

Kernel **#6** was written to boot and read back with matching checksum. The
previous boot/modules were backed up. After a charger reboot, Wi-Fi did not
return during observation. Moving the cable to the laptop exposed USB and
kernel #6. The user confirmed **only moving the cable, with no held Power
reset**. Uptime placed Linux startup around cable transfer rather than the
original reboot request. The stalled stage remains unidentified; reproduce it
with monitored charger power and boot logging before claiming a fix.

Kernel #6 passed repeat Linux RNDIS/NCM DHCP/SSH, descriptor and Docker HTTPS
checks while the display slept. Mode was restored to RNDIS; laptop input remains
limited to 500 mA.

A separate Wi-Fi issue appeared: association succeeded but the DHCP lease
expired and subsequent acquisition failed. The router supplied 120-second
leases. Manual reactivation produced a matching REQUEST/ACK and 8/8 short pings,
then the connection failed again. That is not a stability result. Signal was
**−81 dBm** on 2.4 GHz; power saving was already off. Improve RF/network
conditions before attributing DHCP failures to the kernel.

The temporary power recorder collected 25 laptop-USB samples. The user could
not move the phone to a charger/near the AP, so no #6 DCP samples were collected.
The temporary service/scripts were removed; logs remain locally and on the
phone. An unlimited-autoconnect experiment was reverted to stored value `-1`.

At the end of that phase: kernel #6, `running`, zero failed units, Docker and
LCD/USB active; display sleeping automatically; battery 48%, SDP/500 mA, positive
battery current indicating accepted laptop-USB discharge. Wi-Fi had no IPv4.
Recovery access was **USB SSH at `192.168.7.2`**. These readings are historical,
not a statement of the phone's current state.

## Remaining tests

1. Test near the AP on a charger; verify real charging and stable DHCP renewal.
2. Verify #6 boot, battery status/current and RNDIS/NCM transitions on charger;
   repeat reboot while recording boot IDs and reachability times.
3. Physically confirm short Power behavior and test an actual Windows host.
4. Run endurance and real LAN-adapter tests. The 10 MB/s goal is unproven;
   the earlier Wi-Fi measurement was 1.44 MB/s, one direction and one sample.

Fastboot/TWRP packages passed content, checksum, permissions, rootfs policy and
LK memory checks. Offline validation is separate from successful hardware boot.
Publishing is blocked while runtime regression remains unresolved. The generic
public rootfs has not been freshly installed; hardware tests updated an already
installed private rootfs.

Local logs: `out/recovery-2026-10-30/`. Machine report:
`out/validated/server-console-runtime.json`. Credentials/Wi-Fi remain private.
The previous release is retained at `out/known-good-server-2026-10-29/`; the
phone's pre-#6 backup is `/root/mi5-before-charging-fix-2026-10-30/`.
This update did not format userdata. No GitHub remote/publication was performed.

### Driver research

The [original 2025 ath10k patch](https://lists.infradead.org/pipermail/ath10k/2025-June/016313.html)
bounds recovery after repeated PCIe loss. Its `fail_cont_count` mechanism and
four-failure limit already exist in local Linux 7.0 `ath10k/core.c`; reapplying
it would not be a new fix. Current shutdown/boot logs are still needed to
establish whether Wi-Fi/PCIe is involved.

### Offline validation at this stage

- 12 server tests covered LCD, USB lifecycle, DHCP isolation, PCI enumeration
  and DWC3 current policy.
- Installer/layout/initramfs tests and 32 rootfs checks passed.
- 83 required kernel settings and all three LK boot-image layouts passed.
- Sparse expansion matched the raw rootfs hash.
- Both ZIPs passed payload/checksum/config checks; seven artifacts were recorded
  in `SHA256SUMS` and `build-provenance.json`.
- Runtime regression remained open; no GitHub publication.

## Follow-up: Power/Home did not wake the display

The user reported that Power/Home could not light the LCD. USB showed Linux
still running on the same #6 boot ID; console opened five input devices.
`mi5-console wake` set awake, brightness/actual_brightness 819 and framebuffer
blank 0. The user physically confirmed the LCD lit, establishing command wake.

Power/Home IRQs were zero. PMIC Power and Home GPIO34 matched the backed-up
Android DT. Synthetic native evdev Power slept the display and Home woke it,
verifying handler logic and event layout, **not physical buttons**. The user
then confirmed two short Power presses and one Home press during capture; no
events or IRQs arrived. The hardware/initialization cause remained unresolved.

The phone's timeout was temporarily set to **0**, keeping brightness 20%, to
avoid automatic sleep during diagnosis. Prior config is saved at
`/root/mi5-lcd-wake-before-2026-10-30/mi5-console`; the public image still defaults
to 300 seconds. Evidence: `out/lcd-wake-2026-10-30/`.

### Live Power-driver reinitialization

Only selected PM8994 debugfs registers were read. IRQ enable `0x815` and
Power/Resin edge/polarity were `0x03`. Status `0x810` and Home GPIO were read
without register writes. A held-button level comparison was not confirmed by
the user, so unchanged idle levels cannot establish a faulty button.

The `pm8941-pwrkey` driver was unbound/rebound live. Probe succeeded, console
reopened five inputs, and Linux was not rebooted. A temporary combined
evdev/PMIC/GPIO/IRQ monitor was started; rebind alone was not treated as proof.

### Physical result after reinitialization

The user later confirmed Power could turn the display off. Final state was
`awake=false`; Power IRQ count rose 0 → 18 while Linux remained `running`.
Physical Power worked in that session. Home stayed at IRQ 0 and remains
unverified. No reboot had yet followed the recovery, so startup reliability
was still unknown. Auto-timeout remained 0. Temporary monitoring ended;
final evidence is `out/lcd-wake-2026-10-30/power-working-final.log`.

## Later stability work

See the [next stability report](stability-progress-2026-10-30.md). A subsequent
USB reboot succeeded; physical Power testing after that reboot still awaits
user availability.
