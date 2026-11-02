#!/usr/bin/env bash
# Build actual Armbian userspace with the local Gemini LK/kernel port.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRAMEWORK="${ARMBIAN_BUILD_DIR:-$ROOT/out/armbian-build}"
REVISION=$(cat "$ROOT/armbian/framework-revision")
export GEMINI_PROJECT="$ROOT"
export GEMINI_OUT="${OUT:-$ROOT/out/validated}"
mkdir -p "$GEMINI_OUT"
if [[ ! -d "$FRAMEWORK/.git" ]]; then
    mkdir -p "$FRAMEWORK"
    git -C "$FRAMEWORK" init
    git -C "$FRAMEWORK" remote add origin https://github.com/armbian/build.git
    git -C "$FRAMEWORK" fetch --depth 1 origin "$REVISION"
    git -C "$FRAMEWORK" checkout --detach "$REVISION"
fi
actual=$(git -C "$FRAMEWORK" rev-parse HEAD)
[[ "$actual" == "$REVISION" ]] || {
    echo "Armbian checkout must be $REVISION (got $actual); use an isolated checkout." >&2; exit 1;
}

requested_command="${1:-build}"
command="$requested_command"
if [[ "$command" == userspace ]]; then
    command=build
    export GEMINI_USERSPACE_ONLY=yes
fi
rootfs_type=ext4
# Firmware artifacts contain data only. Their framework adapter intentionally
# skips board loading, so request its archive-only mode to avoid an irrelevant
# check for host kernel ext4 support. Gemini image builds remain ext4.
case "$command" in firmware|firmware-full) rootfs_type=nfs;; esac
if [[ "$command" != configdump && $EUID != 0 ]]; then
    command -v podman >/dev/null || { echo 'Install Podman or use a supported root build host.' >&2; exit 1; }
    container=mi5-armbian-builder
    if ! podman container exists "$container"; then
        podman run -d --privileged --name "$container" --label "gemini.project=$ROOT" \
            -v "$ROOT:$ROOT" -w "$ROOT" \
            "${ARMBIAN_BUILD_CONTAINER_IMAGE:-docker.io/library/ubuntu:24.04}" sleep infinity
    fi
    [[ "$(podman inspect --format '{{index .Config.Labels "gemini.project"}}' "$container")" == "$ROOT" ]] || {
        echo 'Builder container belongs to a different checkout' >&2; exit 1;
    }
    [[ "$(podman inspect --format '{{.State.Running}}' "$container")" == true ]] || podman start "$container"
    exec podman exec -e OUT="$GEMINI_OUT" -e ARMBIAN_BUILD_DIR="$FRAMEWORK" \
        -e GEMINI_DEBUG_ROOTFS="${GEMINI_DEBUG_ROOTFS:-no}" "$container" \
        bash "$ROOT/scripts/armbian-container-entry.sh" "$requested_command"
fi
if [[ "$command" == build && "${GEMINI_USERSPACE_ONLY:-no}" != yes ]]; then
    [[ -f "$GEMINI_OUT/Image.gz" && -d "$GEMINI_OUT/utilities" ]] || {
        echo 'Build the kernel and utilities into OUT first.' >&2; exit 1;
    }
fi
cd "$FRAMEWORK"
oras_options=()
real_oras="$FRAMEWORK/cache/tools/oras/oras_1.3.4_linux_amd64"
if [[ "${ARMBIAN_HTTP1_DOWNLOADS:-yes}" == yes && -x "$real_oras" && "$(uname -m)" == x86_64 ]]; then
    # The current network repeatedly resets large OCI transfers over HTTP/2.
    # Keep the pinned framework and downloaded binary intact; use a local
    # transport wrapper which still lets ORAS verify registry content hashes.
    wrapper_directory="$GEMINI_OUT/host-tools/oras"
    mkdir -p "$wrapper_directory"
    printf '#!/bin/bash\nexec env GODEBUG=http2client=0 %q "$@"\n' "$real_oras" \
        > "$wrapper_directory/oras_1.3.4_linux_amd64"
    chmod 755 "$wrapper_directory/oras_1.3.4_linux_amd64"
    oras_options+=("DIR_ORAS=$wrapper_directory")
fi
exec ./compile.sh "$command" \
    "${oras_options[@]}" \
    USERPATCHES_PATH="$ROOT/armbian/userpatches" \
    ROOTFS_TYPE="$rootfs_type" \
    BOARD=gemini BRANCH=edge RELEASE=bookworm BUILD_DESKTOP=no BUILD_MINIMAL=no \
    KERNEL_CONFIGURE=no COMPRESS_OUTPUTIMAGE=sha DEST_LANG=en_US.UTF-8 \
    SHARE_LOG=no SHARE_LOGS=no SKIP_UPDATE=yes IGNORE_UPDATES=yes \
    ALLOW_ROOT=yes \
    PRESERVE_SDCARD_MOUNT="${GEMINI_DEBUG_ROOTFS:-no}" \
    ENABLE_EXTENSIONS=gemini-lk NETWORKING_STACK=network-manager \
    FORCE_USE_RAMDISK=no CONTAINER_COMPAT=yes
