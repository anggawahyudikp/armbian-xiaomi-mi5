#!/bin/sh
# Grow ext4 inside the existing userdata partition; never edit Android's GPT.
set -eu
dev=$(findmnt -n -o SOURCE /) || exit 0
[ -b "$dev" ] || exit 0

echo "gemini-resize-root: resizing $dev to fill partition..."
if resize2fs "$dev"; then
    echo "gemini-resize-root: successfully resized root filesystem."
    mkdir -p /var/lib
    touch /var/lib/gemini-resize-root.done
else
    echo "gemini-resize-root: resize2fs failed, will retry next boot."
    exit 1
fi
