#!/usr/bin/env bash
# Install build dependencies for gemini mainline kernel & Armbian distribution.
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
	exec sudo "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
	git make podman uidmap \
	gcc-aarch64-linux-gnu g++-aarch64-linux-gnu libc6-dev-arm64-cross \
	bc bison flex libssl-dev libncurses-dev libelf-dev \
	device-tree-compiler \
	cpio gzip pigz xz-utils zip python3 \
	abootimg android-sdk-libsparse-utils \
	mmdebstrap qemu-user-static arch-test \
	picocom minicom rsync mtools

echo "Dependencies installed successfully."
