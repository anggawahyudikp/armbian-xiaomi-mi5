# Ubuntu live hardware dump

> Historical August 2026 Linux/Ubuntu record. Current installation and load
> rules are in the [flash guide](flash-guide.md) and
> [LK memory audit](bootloader-memory-2026-10-29.md).

Dump taken on 6.1 umeko Ubuntu before the 7.0 jump. Raw logs are gitignored. Use this as a hardware map, not as a serial/MAC dump.

Confirmed: `ath10k_pci` QCA6174 → `wlp1s0` (not WCN3990/SNOC). Panel JDI R63452. Touch Synaptics S3330. GPU Adreno 530 zap path under `qcom/msm8996/gemini/`.

## August 27 capture details

USB serial was `/dev/ttyACM0` on that host. The RTC remained at 2025-12-14,
so dump directory timestamp `20251214-104644` is not the actual capture date.
Raw local evidence lives under `inventory/2026-08-27-ubuntu/hw-dump/`.

| Item | Observation |
|---|---|
| Kernel | `6.1.14-umeko-rv0` #1 SMP PREEMPT, 2024-05-07 |
| DT | Xiaomi Mi 5; `xiaomi,gemini`, `qcom,msm8996` |
| Memory | MemTotal 2,763,876 kB |
| Root | UFS sda15, label rootfs; UUID changes on reinstall |
| Display | Connected card0-DSI-1, 1080×1920, msmdrmfb |
| GPU | b00000.gpu loaded pm4/pfp/gpmu firmware |
| Touch | S3330, rmi4 I2C 2-0020, firmware ID 2613032 |
| Buttons | pm8941_pwrkey, pm8941_resin, gpio-keys |
| Haptics | drv260x at I2C 1-005a |
| Battery | 98%, 3000 mAh design, 4.354 V, Li-ion, USB SDP |
| Wi-Fi | QCA6174 hw3.2 at 0000:01:00.0, wlp1s0 DOWN |
| USB | Serial gadget; no usb0/RNDIS address |

Other I2C devices: 0-0028, 1-0030 (lp5562, probe −22), 1-0047, 1-005a,
2-0020. Warnings to monitor on 7.0: missing ADSP firmware, rmtfs memory assign
−22, touch VIO dummy regulator despite working touch, lp5562 probe −22, WLED
OVP IRQ −ENXIO, Adreno vdd/vddcx dummy regulators and PSCI PC mode −1.
These observations supported using upstream Gemini DTS, ATH10K_PCI rather than
SNOC, MSM DRM rather than simplefb alone, and treating absent ADSP as a firmware
problem rather than guessing a different device tree.
