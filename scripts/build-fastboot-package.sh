#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
python3 "$ROOT/scripts/verify-package-inputs.py" "$OUT"
STAGING=$(mktemp -d "$OUT/fastboot-staging.XXXXXX")
trap 'rm -rf "$STAGING"' EXIT
cp "$OUT/boot.img" "$OUT/rootfs.img" "$STAGING/"
cp "$ROOT/scripts/fastboot-install.py" "$STAGING/install.py"
cp "$ROOT/scripts/boot_layout.py" "$STAGING/boot_layout.py"
cp "$ROOT/config/gemini-lk.json" "$STAGING/gemini-lk.json"
cp "$ROOT/scripts/backup-device.py" "$STAGING/backup-device.py"
cat > "$STAGING/flash-all.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/install.py" "$@"
EOF
cat > "$STAGING/flash-all.bat" <<'EOF'
@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python install.py %*
) else (
  py -3 install.py %*
)
if errorlevel 1 pause
EOF
chmod 755 "$STAGING/flash-all.sh"
cat > "$STAGING/README.txt" <<'EOF'
Armbian community port for Xiaomi Mi 5 (gemini), stock LK bootloader.
Requires Python 3.11+, fastboot 37.0.1 or newer and an unlocked bootloader.
Run flash-all.sh on Linux/macOS or flash-all.bat on Windows.
Installation ERASES ALL Android userdata. Make your own data backup first.
The installer verifies checksums, device product, unlock, partition sizes and
the bootloader download limit before the first write. It caps transfers at
the smaller of 256 MiB and that limit; the boot image must fit a raw transfer.
Progress is streamed during flashing. Fastboot 34.0.5 stalled in device tests;
Google Platform-Tools 37.0.1 completed the tested large-image installation.
It never flashes recovery, bootloader or radio.
Run backup-device.py while this rooted phone is still in Android, then supply
--device-proof <backup-directory>/metadata.json to flash-all.sh / flash-all.bat.
This is required even when product says gemini: the aboot firmware hash must
match the load-address profile used to build the image. Generic MSM8996 also
requires the Gemini identity and matching serial from that proof.
First login follows Armbian's normal password-change and user-creation flow.
This is experimental hardware support; see the repository's current worklog.
EOF
(
    cd "$STAGING"
    sha256sum boot.img rootfs.img > SHA256SUMS
)
python3 - "$STAGING" "$OUT/${RELEASE_BASENAME}_fastboot.zip" <<'PY'
import pathlib, sys, zipfile
source, output = map(pathlib.Path, sys.argv[1:])
temporary = output.with_suffix('.zip.tmp')
with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted(source.iterdir()):
        archive.write(path, path.name)
temporary.replace(output)
print(output)
PY
