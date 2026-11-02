#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
if [[ $EUID != 0 ]]; then
    exec podman unshare "$0" "$@"
fi
python3 "$ROOT/scripts/verify-package-inputs.py" "$OUT" --twrp
STAGING=$(mktemp -d "$OUT/twrp-staging.XXXXXX")
trap 'rm -rf "$STAGING"' EXIT
mkdir -p "$STAGING/META-INF/com/google/android"
install -m755 "$ROOT/scripts/twrp-update-binary.sh" "$STAGING/META-INF/com/google/android/update-binary"
touch "$STAGING/META-INF/com/google/android/updater-script"
cp "$OUT/boot.img" "$STAGING/"
# Always regenerate: a previous tarball must never survive a rootfs rebuild.
compressor=(gzip -6)
if command -v pigz >/dev/null; then
    compressor=(pigz -6 -p 2)
fi
tar --numeric-owner -cf - -C "$OUT/rootfs" . | "${compressor[@]}" > "$STAGING/rootfs.tar.gz"
stat -c%s "$OUT/rootfs.ext4" > "$STAGING/rootfs-min-bytes"
python3 - "$ROOT/config/gemini-lk.json" "$STAGING/bootloader-sha256" <<'PY'
import json, pathlib, sys
pathlib.Path(sys.argv[2]).write_text(json.loads(pathlib.Path(sys.argv[1]).read_text())['aboot_sha256'] + '\n')
PY
(
    cd "$STAGING"
    sha256sum boot.img rootfs.tar.gz rootfs-min-bytes bootloader-sha256 > SHA256SUMS
)
python3 - "$STAGING" "$OUT/${RELEASE_BASENAME}_twrp.zip" <<'PY'
import pathlib, sys, zipfile
source, output = map(pathlib.Path, sys.argv[1:])
temporary = output.with_suffix('.zip.tmp')
with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_STORED) as archive:
    for path in sorted(source.rglob('*')):
        if path.is_file():
            archive.write(path, path.relative_to(source))
temporary.replace(output)
print(output)
PY
