# English language rollout — 30 October 2026

The project now uses English for its documentation, authored UI messages,
installer/helper output, diagnostics and legacy HUD. Localized duplicate pages
were consolidated into English canonical pages. Important historical hardware,
boot, display and recovery findings were retained and explicitly marked as
historical. Local pre-change copies are under `out/language-2026-10-30/before/`.
Git history was not rewritten.

## On the phone

- System locale changed from id_ID.UTF-8 to en_US.UTF-8.
- Indonesian LANG/LANGUAGE/LC_ALL overrides in the user's Bash configuration
  were backed up and removed. The login profile exports English UTF-8 settings.
- SSH SetEnv overrides client-forwarded language variables. `sshd -t` passed
  before reloading the service; existing connections were not interrupted.
- A fresh Wi-Fi SSH login deliberately forwarded Indonesian settings. `locale`
  still reported English in every category, `nmcli` reported `connected`, and
  a login shell retained en_US.UTF-8. Evidence: `ssh-english.log` locally.
- English Wi-Fi helper and matching rebuilt ARM64 HUD were installed together
  while the legacy HUD was inactive. The active LCD console service was not
  replaced or restarted. Native hashes matched the local sources/build.
- The helper's empty-input message and `mi5-config status` were verified in
  English. No Wi-Fi profile, credentials, host keys or time zone were changed.

Reconnect existing SSH sessions to receive the new language environment.

## Build and checks

The generic rootfs generates en_US.UTF-8 and includes the same system, shell and
SSH policy. The Armbian framework build also requests English explicitly.
Twenty server tests and boot/installer/layout tests passed. All 78 C Wi-Fi assertions and the shell flow tests
passed for success, missing/wrong passwords, fallback, forgetting and English
error classification. ARM64 board utilities rebuilt successfully. The compiler
still reports existing path/string truncation warnings in legacy programs;
this translation does not establish that those warnings are fixed.

The rootfs passed 38 checks, including actual target locale availability and
English configuration. A heuristic scan of 195 current nonignored project text
files found no remaining Mandarin or Indonesian candidates. Local Markdown
links were checked with no broken targets. The scan excludes third-party
binaries and historical Git objects and is not a formal language detector.

Fastboot/TWRP packages were rebuilt and passed payload/checksum validation.
Completion and hashes are recorded in `out/validated/build-provenance.json`.
The generic image is not reflashed for a language update. Source changes and
native rolling updates remain distinct from a fresh-image hardware test.

## Stability scope

Language changes do not resolve charger-only reboot, physical Power/Home after
reboot, Windows/LAN coverage or 24-hour endurance. The runtime regression flag
and publication block remain enabled. See the [stability plan](stability-plan.md)
and [previous results](stability-progress-2026-10-30.md).

Policy and user commands: [language-policy.md](language-policy.md).
