#!/usr/bin/env bash
# Userspace, base-files and BSP are built by the pinned Armbian framework.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT/scripts/build-armbian.sh" build
