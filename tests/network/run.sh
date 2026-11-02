#!/usr/bin/env bash
# This only changes dummy interfaces in a newly created network namespace.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/scripts/env.sh"
mkdir -p "$OUT"
parent_netns=$(readlink /proc/self/ns/net)
exec podman unshare unshare --net -- python3 "$ROOT/tests/network/test-route-failover.py" \
    "$ROOT/rootfs-overlay/etc/NetworkManager/conf.d/20-gemini-priority.conf" \
    --parent-netns "$parent_netns" --report "$OUT/network-route-validation.json"
