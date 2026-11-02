# Stability follow-up — 30 October 2026, 09:46 WIB

The first stable release targets Wi-Fi, the existing battery, USB-port charging,
LCD console, SSH and light Docker applications. Direct battery-connector supply
and reserving USB-C for a LAN adapter are deferred hardware work.

## Observed evidence

The same boot ID remained active after the earlier USB reboot. Uptime was
approximately 85 minutes. The health history contained 41 samples from that
boot, spanning uptime 94.09 to 5122.32 seconds:

- Wi-Fi interface state was up in all 41 samples.
- SSH, Docker, console and NetworkManager services were active in all samples.
- DHCP renewals were still arriving, approximately every 54 seconds in the
  recent journal excerpt.
- Highest sampled CPU temperature was 63.3°C.
- No systemd units were failed at the final check.
- The selected kernel-error search found a QCA6174 board-2 lookup warning;
  the final check still showed a connected IPv4 interface.

These are sampled idle/light-use observations, not proof of uninterrupted
connectivity, a representative application workload or 24-hour stability.
No additional heavy workload or reboot was started.

## Critical power limitation

Battery fell from 44% to **3%** while attached to laptop USB. The driver still
reported `Charging`; capacity trend proves that label is insufficient evidence
of net charging. Device testing was stopped and the user was asked to move to
a charger or choose an orderly shutdown. No shutdown or physical cable move
is assumed without the user's response.

Further charger/reboot/endurance tests require a suitable external supply and
adequate battery charge. The [stability gate](stability-plan.md) remains open;
no stable release or publication is claimed.

Private evidence: `out/stability-followup-2026-10-30/audit.log`.

## User decision

The user requested leaving the phone powered on with the existing laptop-USB
connection to observe whether capacity recovers. No shutdown is authorized.
Additional device load tests remain deferred; the existing bounded health timer
continues recording. No improvement in charging is assumed from that decision.
