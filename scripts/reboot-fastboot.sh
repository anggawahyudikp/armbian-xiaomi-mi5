#!/usr/bin/env bash
# Wait for LK fastboot after the phone reboots into the bootloader.
# Do not write to USB ACM: opening ttyACM0 fights getty, garbles
# "reboot-fastboot", and can blank the panel while Ubuntu is still running.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WAIT_SEC="${WAIT_SEC:-90}"
SSH_USER="${SSH_USER:-root}"
PHONE_IP="${PHONE_IP:-192.168.7.2}"
PHONE_SERIAL="${PHONE_SERIAL:-}"
export PATH="$HOME/.local/bin:$PATH"

[[ "$WAIT_SEC" =~ ^[0-9]+$ ]] || { echo 'WAIT_SEC must be a nonnegative integer' >&2; exit 2; }
WAIT_SEC=$((10#$WAIT_SEC))
for tool in python3 fastboot timeout ssh; do
	command -v "$tool" >/dev/null || { echo "Missing host tool: $tool" >&2; exit 2; }
done

lk_serial() {
	python3 "$ROOT/scripts/usb_identity.py" --serial "$PHONE_SERIAL"
}

lk_ready() {
	# A stale/composite gadget can produce misleading `fastboot devices` text.
	# Require actual 18d1:d00d enumeration and a bounded protocol response.
	timeout 5 fastboot -s "$1" getvar product
}

if serial=$(lk_serial); then
	if lk_ready "$serial"; then
		echo "==> LK fastboot ready: $serial"
		exit 0
	fi
	echo 'error: LK enumerated but its fastboot protocol is not responding' >&2
	exit 1
else
	code=$?
	[[ "$code" != 2 ]] || exit 2
fi

try_ssh() {
	ping -c1 -W1 "$PHONE_IP" &>/dev/null || return 1
	echo "==> SSH $SSH_USER@$PHONE_IP reboot-fastboot"
	ssh -o BatchMode=yes -o StrictHostKeyChecking=yes \
		-o ConnectTimeout=8 "${SSH_USER}@${PHONE_IP}" \
		'if [ "$(id -u)" -eq 0 ]; then systemctl reboot bootloader; else sudo -n systemctl reboot bootloader; fi' \
		|| true
	return 0
}

if try_ssh; then
	:
else
	echo "==> Do not type reboot-fastboot into the USB serial console"
	echo "    (it races getty and can blank the panel while Ubuntu is still running)."
	echo "    Use the on-screen Fastboot control, or power off and hold Vol- + Power."
fi

echo "==> Waiting up to ${WAIT_SEC}s for USB 18d1:d00d (a black screen or FASTBOOT text is not enough)"
deadline=$((SECONDS + WAIT_SEC))
while ((SECONDS < deadline)); do
	if serial=$(lk_serial 2>/dev/null) && lk_ready "$serial"; then
		echo "==> LK fastboot ready: $serial"
		exit 0
	fi
	sleep 1
done

echo "error: no fastboot device after ${WAIT_SEC}s" >&2
echo "Keys: power off, then Vol- + Power. Success is lsusb 18d1:d00d, not 0525:a4a7." >&2
lk_serial || true
lsusb | grep -iE '0525|18d1|d00d' || true
exit 1
