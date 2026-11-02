# Xiaomi Mi 5 / MSM8996, stock LK bootloader. Local community port, not official support.
declare -g BOARD_NAME="Xiaomi Mi 5"
declare -g BOARD_VENDOR="xiaomi"
declare -g BOARDFAMILY="msm8996-gemini"
declare -g KERNEL_TARGET="edge"
declare -g KERNEL_TEST_TARGET="edge"
declare -g BOOTCONFIG="none"
declare -g EXTRAWIFI="no"
declare -g SERIALCON="ttyGS0"
declare -g BOARD_FIRMWARE_INSTALL="-full"
enable_extension "gemini-lk"

# Runs before extension initialization in the pinned framework. Gemini images
# are created by mkfs.ext4 -d, never mounted by the host, so host ext4 kernel
# support is irrelevant (and cannot be loaded from a rootless container).
function check_filesystem_compatibility_on_host() {
    [[ "$ROOTFS_TYPE" == ext4 ]] || exit_with_error "Gemini requires ext4 output"
    display_alert "Gemini image uses userspace mkfs.ext4 -d" "No host filesystem mount required" "info"
}
