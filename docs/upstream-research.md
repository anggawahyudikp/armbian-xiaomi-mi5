# Upstream research (2026-08-27)

> Historical August 2026 Linux/Ubuntu record. Current installation and load
> rules are in the [flash guide](flash-guide.md) and
> [LK memory audit](bootloader-memory-2026-10-29.md).

Goal: move gemini from `6.1.14-umeko-rv0` to Linux **7.0**.

Mainline already has `arch/arm64/boot/dts/qcom/msm8996-xiaomi-gemini.dts` (`xiaomi,gemini`, `qcom,msm8996`). Panel `jdi,fhd-r63452`, touch `syna,rmi4-i2c@20`, GPU zap `qcom/msm8996/gemini/a530_zap.mbn`.

The 6.1 umeko version string matches msm8996-mainline tag `v6.1.14-msm8996`. Linux 7.0 from torvalds already includes the gemini DTS. Local changes stay in `overlays/` and are `#include`d, not patched into upstream files.

## Sources and differences recorded at the time

| Source | Purpose |
|---|---|
| torvalds v7.0 | Mainline build baseline |
| msm8996-mainline Linux | Snapdragon 820 community patches; board IDs 31 and 32 |
| postmarketOS device-xiaomi-gemini | Uses linux-postmarketos-qcom-msm8996; maintained by cunidev / Raffaele Tranquillini |
| gemini-pmos-tweaks | Userspace tweaks rather than a kernel tree |

At the time msm8996-mainline had no 7.0 branch; stable was 6.19.5-msm8996 and
staging was msm8996-staging. This is a historical observation, not a current
upstream-version claim. Staging differences included second board-id 32,
3000000 µAh design charge, GPU zap node structure, simplified sound model,
haptics enable GPIO and mdss_te_sleep pinctrl. A directly packaged DTB does not
necessarily depend on LK selecting a board-id match.

Authors recorded: Raffaele Tranquillini (Gemini DTS/pmOS), Yassine Oudjana
(common DTS/board-id32), Krzysztof Kozlowski (touch VIO/UFS supplies). Historical
commits included `4ac46b3682c5` (initial support), `21fc24ee9c59` (touch VIO) and
`38f6ac152fa6` (UFS pad supply).

The neighboring ginkgo project supplied a reusable build sequence, but uses
SM6125/eMMC/header-v2 rather than Gemini's MSM8996/UFS/header-v0. Do not copy its
clock/pinctrl/interconnect, dtbo/vbmeta or load assumptions. Current effective
LK addresses supersede old header-only notes; see the
[bootloader audit](bootloader-memory-2026-10-29.md).
