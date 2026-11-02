# Public source distribution

The canonical public repository is
[anggawahyudikp/armbian-xiaomi-mi5](https://github.com/anggawahyudikp/armbian-xiaomi-mi5).
Project documentation, interfaces, issue templates and CI messages use English.

Version 0.1.0 is distributed as source with GPL-2.0 licensing for project code
and preserved third-party notices. See LICENSE and THIRD_PARTY_NOTICES.md.
The GitHub tag and source release are not firmware-equipped installation images.
Build images locally after preparing the required [firmware inputs](firmware-inputs.md).

The public Git history starts from the reviewed source snapshot. Private local
history, credentials, full diagnostic archives, original phone backups,
proprietary firmware and third-party reference images are not uploaded.
Generated board-program binaries are omitted; their C sources and build scripts
are included. This keeps the working development checkout and its private
recovery material separate from the public distribution.

The publication changes from the hardware-qualified source are documentation,
publication metadata, pinned host CI, omission of generated/private third-party
inputs an explicit skip for the optional legacy-firmware test fixture when absent,
and a pinned upstream callback fixture that exercises the actual charger patch
without requiring a full local kernel checkout. Firmware, kernel and functional runtime code are not changed by this
publication preparation. Hardware qualification scope is documented in the
[stability report](stable-release-0.1.0.md).

Use root for SSH after changing the initial root password during Armbian
onboarding. Public examples use root@192.168.7.2 for USB and root@MI5_WIFI_IP
for Wi-Fi; no personal account name or password is shipped. First login still
follows Armbian's password-change and additional-user creation flow.

CI runs host tests with synthetic inputs and mocks; it does not access a phone,
include proprietary firmware, build a full image or certify additional hardware.
See CONTRIBUTING.md for local checks and SECURITY.md for private reporting.
