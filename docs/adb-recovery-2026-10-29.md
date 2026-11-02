# ADB inspection after Android returned — 29 October 2026

**Update:** the logging candidates below were later rejected after auditing
aboot's effective addresses. They were moved to
`out/incompatible-stock-lk-2026-10-29/logging/`. Logging support built
successfully but did not solve the memory overlap. See the
[bootloader audit](bootloader-memory-2026-10-29.md).

Android identified the phone as Mi 5 `gemini`; Magisk root worked. This
inspection did not reboot, RAM boot, flash or change phone configuration.
Physical reset access was unavailable, so another boot test was deferred.

| Check | Result |
|---|---|
| Android/kernel | Android 11, FloppyKernel 3.18.124 |
| Actual SoC | MSM8996, soc_id 246, revision 3.1 |
| Vendor DT model | MSM 8996 v3 + PMI8994 MTP |
| Android boot reason | `shutdown,battery` |
| Initial battery | 3%, Charging, approximately 25°C |
| Boot/recovery | 64 MiB each; hashes matched prior backups |
| Pstore | Mounted, no previous boot log files |
| last_kmsg/dropbox kernel logs | Not found at inspected paths |

The boot reason and battery state do not establish where the previous Linux
boot failed. No panic/console logs were recovered. Successful fastboot transfer
does not prove the kernel reached init or USB.

Full local evidence is under `out/hardware-2026-10-29/adb-recovered/`, including
`report.json`, Android dmesg/config, analyzed vendor DTB and backup checks.
`out/` is Git-ignored.

## Diagnostic logging changes

The existing build enabled `CONFIG_PSTORE` and `CONFIG_PSTORE_RAM`, but not
`CONFIG_PSTORE_CONSOLE` or `CONFIG_PSTORE_PMSG`; Android enabled both. Console
capture is needed to preserve messages when failure does not reach an oops or
panic, as explained in the local kernel's `fs/pstore/Kconfig`.

Android and Linux DT agreed on this reserved area:

| Parameter | Value |
|---|---|
| Base / total size | `0x92900000` / `0x100000` |
| Record | `0x8000` |
| Console | `0x80000` |
| Pmsg | `0x40000` |
| Ftrace reservation | `0x20000` |

The optional [logging fragment](../config/diagnostic-logging.fragment) enables
console and pmsg. It used separate cache `out/kernel-diagnostic-logging/` and
output `out/diagnostic-logging/`. Both RAM images passed header, initramfs,
module dependency, memory-range and required-config checks. Extracted DTB and
config matched Android's ramoops layout. Evidence files were
`logging-validation.json`, `boot-validation.json`, `usb-debug-validation.json`
and `SHA256SUMS`. Neither candidate was run on the phone at this point; both
were subsequently rejected for the LK overlap described above. The minimal USB
variant disables display/GPU/PCIe/UFS/charger/FG and tests basic boot/USB only.
Logging availability does not establish bootability, and logs can disappear
when RAM loses power during reset.

Later readings still showed 3%/Charging near 25°C. Voltage rose from about
3.625 V to 3.677 V and the charge counter increased, but no battery percentage
increase was observed during this inspection.

Reference: [kernel ramoops documentation](https://docs.kernel.org/admin-guide/ramoops.html).
