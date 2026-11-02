# Armbian framework integration for an existing Android GPT and LK bootloader.
# Pinned to armbian/framework-revision. No partition table, loop image or U-Boot
# is needed: userdata is a single ext4 image and boot is a separate Android image.

function extension_prepare_config__gemini_paths() {
    : "${GEMINI_PROJECT:?Set GEMINI_PROJECT to this repository}"
    : "${GEMINI_OUT:?Set GEMINI_OUT to the verified kernel output directory}"
    [[ "$BOARD" == gemini ]] || exit_with_error "gemini-lk is only for BOARD=gemini"
    add_packages_to_image busybox-static wpasupplicant wireless-regdb rfkill iw bluez e2fsprogs openssh-server python3 dnsmasq-base kbd console-setup
}

function extension_finish_config__gemini_output_handler() {
    [[ "$(declare -f prepare_partitions)" == *"Build Gemini kernel first"* ]] || \
        exit_with_error "Gemini image output handler was not installed"
    [[ "$(declare -f create_image_from_sdcard_rootfs)" == *"rootfs-validation.json"* ]] || \
        exit_with_error "Gemini rootfs output handler was not installed"
}

function add_host_dependencies__gemini_packaging() {
    EXTRA_BUILD_DEPS+=("build-tools::python3" "build-tools::android-sdk-libsparse-utils" "build-tools::cpio" "build-tools::zip")
}

function host_dependencies_ready__gemini_binfmt() {
    # Ubuntu's qemu-user-static ships systemd binfmt snippets rather than the
    # update-binfmts database expected by this framework revision. A rootless
    # container has its own initially empty binfmt namespace.
    if ! arch-test arm64 >/dev/null 2>&1; then
        mountpoint -q /proc/sys/fs/binfmt_misc || \
            mount -t binfmt_misc binfmt_misc /proc/sys/fs/binfmt_misc
        [[ -f /usr/lib/binfmt.d/qemu-aarch64.conf ]] || exit_with_error "Missing ARM64 binfmt definition"
        cat /usr/lib/binfmt.d/qemu-aarch64.conf > /proc/sys/fs/binfmt_misc/register
    fi
    arch-test arm64 || exit_with_error "ARM64 userspace emulation failed"
}

function pre_install_distribution_specific__gemini_container_devices() {
    # Podman's device nodes are individual mounts. The framework's plain bind
    # of /dev omits those submounts and exposes mode-0700 placeholder files.
    # Bind only the harmless character devices needed by package scripts; keep
    # the framework's private devpts and avoid exposing any host block devices.
    local device
    for device in null zero full random urandom tty; do
        [[ -c "/dev/$device" ]] || exit_with_error "Missing build character device $device"
        if [[ ! -c "$SDCARD/dev/$device" ]]; then
            [[ -e "$SDCARD/dev/$device" ]] || touch "$SDCARD/dev/$device"
            mount --bind "/dev/$device" "$SDCARD/dev/$device"
        fi
        [[ -c "$SDCARD/dev/$device" ]] || exit_with_error "Invalid build character device $device"
    done
    chroot "$SDCARD" /usr/sbin/runuser -u _apt -- /bin/sh -c \
        'command -v gpgv >/dev/null && test -c /dev/null' || \
        exit_with_error "APT sandbox cannot use build devices"
}

function pre_install_distribution_specific__gemini_apt_probe() {
    [[ "${GEMINI_DEBUG_ROOTFS:-no}" == yes ]] || return 0
    install -m755 "$GEMINI_PROJECT/scripts/probe-apt-environment.sh" "$SDCARD/tmp/gemini-apt-probe"
    chroot "$SDCARD" /bin/bash /tmp/gemini-apt-probe > "$GEMINI_OUT/apt-environment.log" 2>&1
    rm -f "$SDCARD/tmp/gemini-apt-probe"
}

# The following two overrides replace only the framework's whole-disk image
# assembly. All normal Armbian package/rootfs/customization stages still run.
function prepare_partitions() {
    [[ "$BOARD" == gemini ]] || exit_with_error "Unexpected board in Gemini image builder"
    if [[ "${GEMINI_USERSPACE_ONLY:-no}" == yes ]]; then
        display_alert "Exporting Armbian userspace before kernel assembly" "Gemini userspace stage" "info"
        return 0
    fi
    [[ -f "$GEMINI_OUT/Image.gz" ]] || exit_with_error "Build Gemini kernel first"
    [[ -f "$GEMINI_OUT/msm8996-xiaomi-gemini.dtb" ]] || exit_with_error "Missing Gemini DTB"
    [[ -d "$GEMINI_OUT/modules/lib/modules" ]] || exit_with_error "Missing kernel modules"
    run_host_command_logged env OUT="$GEMINI_OUT" ROOTFS="$SDCARD" \
        "$GEMINI_PROJECT/scripts/configure-rootfs.sh"
}

function create_image_from_sdcard_rootfs() {
    # Preserve the completed Armbian rootfs before framework cleanup removes SDCARD.
    mkdir -p "$GEMINI_OUT/rootfs"
    run_host_command_logged rsync -aHAX --delete "$SDCARD/" "$GEMINI_OUT/rootfs/"
    if [[ "${GEMINI_USERSPACE_ONLY:-no}" == yes ]]; then
        # This is an intermediate tree, not an installable image or a passed
        # validation result. Kernel/modules and Gemini customization come next.
        printf 'Armbian userspace assembled; kernel integration pending\n' > "$GEMINI_OUT/userspace-built"
        return 0
    fi
    local modules=("$GEMINI_OUT/modules/lib/modules/"*)
    local kernel_release="${modules[0]##*/}"
    run_host_command_logged python3 "$GEMINI_PROJECT/scripts/verify-rootfs.py" \
        "$GEMINI_OUT/rootfs" --kernel-release "$kernel_release" --report "$GEMINI_OUT/rootfs-validation.json"
    run_host_command_logged env OUT="$GEMINI_OUT" ROOTFS="$GEMINI_OUT/rootfs" \
        "$GEMINI_PROJECT/scripts/build-rootfs-image.sh"
    printf '%s\n' "$GEMINI_OUT/rootfs.ext4" > "$GEMINI_OUT/armbian-rootfs-built"
}
