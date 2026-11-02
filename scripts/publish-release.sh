#!/usr/bin/env bash
# Prepare reviewable release notes; publishing requires an explicit flag.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/env.sh"
mode="${1:---prepare}"
[[ "$mode" == --prepare || "$mode" == --publish ]] || { echo 'Usage: publish-release.sh --prepare | --publish OWNER/REPO' >&2; exit 2; }
version=$(python3 "$ROOT/scripts/project_metadata.py" --field version)
fastboot="${RELEASE_BASENAME}_fastboot.zip"
twrp="${RELEASE_BASENAME}_twrp.zip"
for name in "$fastboot" "$twrp" SHA256SUMS release-validation.json build-provenance.json; do
 [[ -f "$OUT/$name" ]] || { echo "Missing validated artifact: $OUT/$name" >&2; exit 1; }
done
python3 - "$OUT" <<'PY'
import json,pathlib,sys
out=pathlib.Path(sys.argv[1])
assert json.loads((out/'release-validation.json').read_text())['passed']
assert json.loads((out/'build-provenance.json').read_text())['offline_validation_passed']
PY
cat > "$OUT/release-notes.md" <<NOTES
# Armbian for Xiaomi Mi 5 — v${version}

Experimental community port for Xiaomi Mi 5 (gemini / MSM8996).
Debian Bookworm ARM64 userspace built by the pinned Armbian framework.

- ${fastboot}: PC installer with device and firmware preflight checks.
- ${twrp}: recovery installer; actual recovery installation is not hardware-verified.
- SHA256SUMS and build-provenance.json: artifact identity and validation scope.

Installation erases Android userdata. Boot/recovery backups do not include personal data.
Production boot.img requires an installed Gemini rootfs; RAM-only checks use boot-diagnostic.img.
First login creates user credentials. No personal passwords, Wi-Fi profiles or SSH keys are shipped.

Features: LCD Linux console with display-only sleep; Wi-Fi primary; USB network + serial management.
USB RNDIS targets Linux and Windows 10/11; NCM is optional for Linux/Windows 11.
See server-console-runtime.json and the repository worklog for actual hardware test coverage.
Long-duration stability, sustained performance and physical USB Ethernet failover remain separate tests.
NOTES
python3 - "$OUT" "$mode" <<'PY'
import json, pathlib, sys
out, mode = pathlib.Path(sys.argv[1]), sys.argv[2]
runtime = out / 'server-console-runtime.json'
state = json.loads(runtime.read_text()) if runtime.exists() else {}
if state.get('hardware_regression_unresolved', True):
    notes = out / 'release-notes.md'
    reason = state.get('cause', 'Hardware stability evidence is missing or incomplete.')
    notes.write_text(notes.read_text() + '\nDevice test: unresolved regression. ' + reason + '\n')
    if mode == '--publish':
        raise SystemExit('Resolve the recorded device regression before publishing this preview.')
PY
printf 'Prepared %s\n' "$OUT/release-notes.md"
if [[ "$mode" == --publish ]]; then
 repo="${2:?Pass OWNER/REPO explicitly}"
 [[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || exit 2
 python3 "$ROOT/tests/boot/verify-release.py" "$OUT"
 gh release create "v$version" --repo "$repo" --title "Armbian for Xiaomi Mi 5 v$version" \
    --prerelease --notes-file "$OUT/release-notes.md" \
    "$OUT/$fastboot" "$OUT/$twrp" "$OUT/SHA256SUMS" "$OUT/build-provenance.json"
fi
