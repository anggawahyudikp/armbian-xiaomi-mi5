# Mi 5 bootloader memory findings — 29 October 2026

Earlier boot checks assumed LK used Android header addresses directly. That
assumption was wrong for this phone's aboot. Earlier boot/package approvals
were revoked; affected images/ZIPs moved to
`out/incompatible-stock-lk-2026-10-29/`, including the `logging/` candidate.

The bootloader was not changed. Its 2 MiB snapshot was read through root ADB,
transferred as base64 and verified against the partition SHA-256:
`41b215d8606e2d0e7a19dedf503432d7d152b6819fe9623eb35bfca78767b825`.
The binary remains in Git-ignored `out/boot-chain-audit/`.

## Effective address evidence

The aboot ELF has PT_LOAD at `0x92a00000`. ARM disassembly showed the function
at `0x92a3957c` overwriting header addresses regardless of their initial values.
The kernel loading path calls it, including ARM64-aware fastboot boot. The
original function was executed in Unicorn with cached DDR base `0x80000000`
matching the phone. This was local emulation, not execution on the phone.

| Destination | Effective ARM64 address |
|---|---|
| Kernel | `0x80080000` |
| DTB | `0x82800000` |
| Ramdisk | `0x82a00000` |

Changing the ramdisk header to `0x84000000` did not alter these results. ARM32
chooses kernel `0x80008000`; ARM64 always chooses `0x80080000`. Evidence is in
`out/boot-chain-audit/effective-load-audit.json`.

Reproduce the firmware-function audit with:

```bash
python3 tests/boot/audit_aboot.py out/boot-chain-audit/aboot-readonly.bin \
    --report out/boot-chain-audit/aboot-emulation-validation.json
```

The tool checks the ELF hash before using the function offset and verifies
return to the caller. ARM32/ARM64 results matched the profile. Android
`/proc/iomem` also placed the first System RAM bank at `0x80000000`.

Android's running kernel had an in-memory image_size of 41,168,896 bytes and
ended before the DTB. The original diagnostic kernel required 45,416,448 bytes;
the logging candidate 45,547,520 bytes. Both crossed forced DTB/ramdisk addresses.
Their decompressed file sizes also overlapped; this was not just BSS metadata.
The layout error is consistent with failure before USB console, but no earlier
Linux trace was available to establish every cause of failure.

## Replacement build

- Restrict the kernel to Qualcomm platforms. Keep QCA6174, UFS, display, USB
  Ethernet, ZRAM, cgroup and Docker requirements enforced. Enable ramoops
  console/PMSG.
- LK starts the payload at a 512 KiB offset, while the mainline Image declares
  text_offset zero. An ARM64 NOP/branch wrapper with 1.5 MiB padding transfers
  control to the original Image at 2 MiB-aligned `0x80200000`, preserving boot
  argument registers. Maintainers discuss this legacy-firmware strategy; that
  does not mean this port's patch has been accepted upstream.
- `scripts/boot_layout.py` validates the complete ARM64 memory span including
  BSS. The original Image must fit within 38 MiB before the DTB. Wrapper, DTB
  and ramdisk boundaries are independently checked.
- Android headers now reflect actual LK addresses. Inspector/installer reject
  old headers/layouts, unwrapped Images and oversized memory spans even if gzip
  is small.
- Firmware loading rules can differ. The installer requires Gemini identity,
  serial and a matching audited aboot hash. TWRP checks aboot directly before
  formatting. No aboot writes are performed.

Replacement `7.0.0-gemini-lk-dirty` completed at 17:36 WIB. Original Image file
size was 33,282,056 bytes; its ARM64 memory span including BSS was 33,947,648
bytes (32.375 MiB). The wrapped Image starts at `0x80200000`, ends at
`0x82260000`, and leaves 5,898,240 bytes (5.625 MiB) before DTB `0x82800000`.
Actual-build checks passed in `out/boot-chain-audit/compiled-kernel-memory.json`.
Kernel/module builds exited 0; replacement boot/rootfs/packages passed offline
checks. Diagnostic boot then succeeded, followed by installed native Armbian,
Wi-Fi, SSH and Docker. See [progress](bringup-progress-2026-10-29.md) for power
and thermal limitations.

The profile is [gemini-lk.json](../config/gemini-lk.json). Thirteen mocked
installer tests and nine layout tests passed, including wrapper execution under
ARM64 emulation. Minimal/normal diagnostics reached a shell; four CPUs,
read-only UFS, Wi-Fi scan and ZRAM were tested. The USB power-fix kernel also
booted; hardware results remain distinct from offline validation.

The original verifier required 77 settings, including container prerequisites
previously requested only through fragments. Active config passed; copies
missing seccomp filter, pids controller or NAT were rejected. Evidence is
`out/boot-chain-audit/server-config-validation.log`. Native Docker ARM64,
cgroup v2, memory limits and overlay2 later passed. Current builds require 83
settings including USB power, charger, fuel gauge and CPU thermal control.
DTB cooling maps are checked; short stress tests do not establish endurance.

Primary references:

- [ARM64 boot protocol](https://docs.kernel.org/arch/arm64/booting.html).
- [Maintainer discussion of legacy-firmware wrappers/padding](https://lkml.iu.edu/hypermail/linux/kernel/2510.1/02489.html).
- [LK forced-address code for comparison; actual evidence above comes from device firmware](https://github.com/msm8916-mainline/lk2nd/blob/fd380ac637d1af38598e3f3c5321d4c962b96315/app/aboot/aboot.c).
- [Moby kernel configuration check](https://github.com/moby/moby/blob/master/contrib/check-config.sh).
- [Docker cgroup v2 requirements](https://docs.docker.com/engine/containers/runmetrics/#running-docker-on-cgroup-v2).
