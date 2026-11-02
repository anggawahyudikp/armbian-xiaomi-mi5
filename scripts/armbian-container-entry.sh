#!/usr/bin/env bash
# Only invoked inside the isolated, rootless Podman build container.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
if [[ ! -f /var/lib/mi5-builder-ready ]]; then
    apt-get update
    apt-get install -y --no-install-recommends git ca-certificates curl gnupg python3 sudo locales
    touch /var/lib/mi5-builder-ready
fi
exec "$(dirname "$0")/build-armbian.sh" "${1:-build}"
