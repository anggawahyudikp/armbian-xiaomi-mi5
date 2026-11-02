#!/bin/bash
# Build-container diagnostics only; no key material or credentials are printed.
set +e
id
printf 'PATH=%s\n' "$PATH"
ls -l /usr/bin/gpgv /usr/bin/apt-key /bin/sh
command -v gpgv
test -x /usr/bin/gpgv; printf 'root executable check: %s\n' "$?"
/usr/bin/gpgv --version | head -2
/usr/sbin/runuser -u _apt -- /bin/sh -c 'id; printf "PATH=%s\n" "$PATH"; command -v gpgv; test -x /usr/bin/gpgv; printf "sandbox executable check: %s\n" "$?"; /usr/bin/gpgv --version | head -2'
exit 0
