# Security

Do not include passwords, tokens, private keys, Wi-Fi profiles or original phone
backups in public issues. Share a reviewed allowlisted diagnostic summary from
mi5-doctor --json rather than full private journals or configuration archives.

Report security issues through GitHub private vulnerability reporting when it
is enabled for this repository. If that option is unavailable, open a minimal
issue requesting a private reporting channel without including exploit details
or secrets.

The generic image uses Armbian onboarding to replace the initial root password.
Use your own root password or SSH keys. No personal password is distributed.
This is a community port; security updates for distribution packages and the
kernel must be assessed and installed by the operator. See the stability report
for the tested scope and unverified platforms.
