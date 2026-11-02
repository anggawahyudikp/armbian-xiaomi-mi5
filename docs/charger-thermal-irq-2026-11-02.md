# Charger thermal interrupt investigation — 2 November 2026

Final update: the status-aware handler was built and the shutdown regression did not recur during five USB and five charger-runtime reboots. Asserted/read-error protection passed the callback harness; no physical thermal emergency was induced. See the [0.1.0 report](stable-release-0.1.0.md). The investigation checkpoints below are historical.

## Observation

The saved phone journal contains eight short boots, ending in hardware-protection
shutdowns with the reason `Charger thermal emergency`. The installed production
boot hash remained `294e1958...`. A previously verified diagnostic RAM image
booted, and userdata was read without journal replay. The original full backup
and the newly copied journal archive were retained and hash-verified. No new
production image had been flashed at that checkpoint.

The charger callback previously treated every `temp-shutdown` interrupt as an
emergency. Its device-tree interrupt uses both rising and falling edges, so an
interrupt alone does not identify an active alarm. A live status observation is
needed to distinguish an asserted alarm from its clearing transition.

## Source evidence

The local device tree maps `temp-shutdown` to PMI8994 peripheral 0x16, interrupt
1. The charger's register base is 0x1000 and its MISC real-time status offset is
0x610, yielding register 0x1610 and status bit 1. Linux's SPMI interrupt driver
reads the peripheral's real-time status at offset 0x10 and tests the interrupt
bit to obtain its live line level; see the
[pinned Linux implementation](https://github.com/torvalds/linux/blob/028ef9c96e96197026887c0f092424679298aae8/drivers/spmi/spmi-pmic-arb.c).

The [Xiaomi Gemini kernel source](https://raw.githubusercontent.com/MiCode/Xiaomi_Kernel_OpenSource/gemini-m-oss/drivers/power/qpnp-smbcharger.c)
also registers this interrupt for both edges. Its handler logs the event; this
is useful corroboration of edge semantics, not a reason to remove the current
project's shutdown protection.

## Candidate change

The handler now reads live MISC status before choosing its response:

| Observation | Response |
| --- | --- |
| Read succeeds and thermal bit is clear | Log the cleared status and notify the power supply; leave charge/input controls unchanged |
| Read succeeds and thermal bit is set | Retain hardware-protection shutdown and disable charging and USB input, as before |
| Status read fails | Retain the same shutdown path; an unknown status cannot suppress protection |

The interrupt trigger remains both-edge. The existing protection reason and
100 ms forced-shutdown deadline are unchanged. This does not change thermal
thresholds or re-enable a charge path after a fault.

The actual callback is compiled into a host harness with mocked regmap and
power controls. All 256 status values and six read-error/status combinations
passed; the test checks the live register address, shutdown timing and control
call order. All 23 server tests passed. These tests establish software response
semantics, not physical charger behavior.

## Hardware validation still required

The new kernel release is `7.0.0-gemini-lk-clockrtc-chgstatus`. Qualification must
record the actual status values on cold boot, USB boot and charger boot. A clear
status accompanying the formerly fatal transition would support the deassertion
hypothesis. An asserted alarm must still cause protection; it requires further
hardware/driver investigation rather than suppression.

The diagnostic environment reported 27% battery, 25.0°C fuel-gauge temperature
and CPU sensor maximum 47.5°C around 06:07 WIB. Those readings alone cannot
exclude a charger-die fault. Heavy workload tests are deferred until power and
battery conditions are appropriate.

The latest testing authorization ends at 17:00 WIB on 2 November, with test
cleanup at 16:59. Actual elapsed coverage and remaining gates must be reported
without treating a shortened run as a completed 24-hour qualification.
