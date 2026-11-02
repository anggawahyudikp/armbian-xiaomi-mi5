#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
exec python3 "$ROOT/scripts/fastboot-install.py" --directory "$OUT" "$@"
