# Contributing

Use English for code comments, documentation, issues and pull requests.
Read README.md and docs/stable-release-0.1.0.md before changing hardware policy.

Run the host checks from a clean source checkout:

```sh
bash tests/boot/run.sh
python3 -m unittest discover -s tests/server
bash tests/network/run.sh
python3 -m unittest discover -s tests/stability
bash tests/wifi-flow/run.sh
```

Install Python 3, GCC, iproute2 and rootless Podman first. The network runner
uses a private user/network namespace and dummy interfaces; it requires local
namespace support and never changes host routes.

The host suite does not require phone access or proprietary firmware. It does
not replace hardware testing. A firmware-equipped build needs the separate
local inputs documented in docs/firmware-inputs.md.

Describe the problem, resulting behavior, validation and any untested scope in
pull requests. Identify the tested kernel, image and power/network conditions
when reporting device results. Preserve previous failures and distinguish
software tests from hardware observations.

Never commit passwords, tokens, private keys, saved connection profiles,
original phone backups, modem/persist images, personalized rootfs files or raw
private diagnostic archives. Share sanitized summaries with precise scope.

Keep changes to thermal protection, charging, partition layout and boot memory
small and reviewable. Do not weaken protection merely to make a test pass.
