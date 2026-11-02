#!/usr/bin/env bash
# Populate ext4 directly, without loop devices or mounting a host filesystem.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
ROOTFS="${ROOTFS:-$OUT/rootfs}"
IMAGE="${IMAGE:-$OUT/rootfs.ext4}"
SPARSE_IMAGE="${SPARSE_IMAGE:-$OUT/rootfs.img}"
[[ $EUID == 0 ]] || { echo 'Run in the build container or user namespace as root.' >&2; exit 1; }
[[ -f "$ROOTFS/etc/armbian-release" ]] || { echo 'Missing Armbian rootfs' >&2; exit 1; }
[[ "$(cat "$ROOTFS/etc/gemini-rootfs")" == gemini-rootfs-v1 ]] || exit 1
command -v img2simg >/dev/null
PYTHONPATH="$ROOT/scripts" python3 - "$ROOTFS" "$OUT/rootfs-validation.json" <<'PY'
import sys
from artifact_identity import validated_rootfs
validated_rootfs(*sys.argv[1:])
PY
size_mb=$(( $(du -sm "$ROOTFS" | cut -f1) + 768 ))
(( size_mb >= 2048 )) || size_mb=2048
mkdir -p "$(dirname "$IMAGE")" "$(dirname "$SPARSE_IMAGE")"
raw=$(mktemp "${IMAGE}.XXXXXX")
sparse=$(mktemp "${SPARSE_IMAGE}.XXXXXX")
trap 'rm -f "$raw" "$sparse"' EXIT
truncate -s "${size_mb}M" "$raw"
mkfs.ext4 -F -L rootfs -O ^orphan_file -d "$ROOTFS" "$raw"
e2fsck -fn "$raw"
img2simg "$raw" "$sparse"
mv -f "$raw" "$IMAGE"
mv -f "$sparse" "$SPARSE_IMAGE"
trap - EXIT
PYTHONPATH="$ROOT/scripts" python3 - "$OUT" "$IMAGE" "$SPARSE_IMAGE" <<'PY'
import json, pathlib, sys
from artifact_identity import file_sha256
out, raw, sparse = map(pathlib.Path, sys.argv[1:])
validation = json.loads((out / 'rootfs-validation.json').read_text())
report = {'passed': True, 'rootfs_sha256': validation['rootfs_sha256'],
          'kernel_release': validation['kernel_release'],
          'images': {p.name: {'sha256': file_sha256(p), 'bytes': p.stat().st_size}
                     for p in (raw, sparse)}}
(out / 'rootfs-image-validation.json').write_text(json.dumps(report, indent=2) + '\n')
PY
ls -lh "$IMAGE" "$SPARSE_IMAGE"
