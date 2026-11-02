#!/usr/bin/env python3
"""Require matching, current validation results before packaging a release."""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
from artifact_identity import file_sha256, validated_rootfs

parser = argparse.ArgumentParser()
parser.add_argument("output", type=pathlib.Path)
parser.add_argument("--twrp", action="store_true")
args = parser.parse_args()
out = args.output.resolve()
project = pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="gemini-package-check-") as temporary:
    report_path = pathlib.Path(temporary) / "boot.json"
    subprocess.run([sys.executable, str(project / "scripts/inspect-bootimg.py"),
                    str(out / "boot.img"), "--mode", "production", "--require-server-config",
                    "--report", str(report_path)], check=True)
    boot = json.loads(report_path.read_text())
rootfs = json.loads((out / "rootfs-validation.json").read_text())
images = json.loads((out / "rootfs-image-validation.json").read_text())
if not (rootfs.get("passed") is True and images.get("passed") is True):
    raise SystemExit("Rootfs/image validation has not passed")
if len({boot["kernel_release"], rootfs["kernel_release"], images["kernel_release"]}) != 1:
    raise SystemExit("Boot kernel and rootfs modules have different releases")
if rootfs["rootfs_sha256"] != images["rootfs_sha256"]:
    raise SystemExit("Image was built from another rootfs; rebuild the image")
if args.twrp:
    validated_rootfs(out / "rootfs", out / "rootfs-validation.json")
    raw = out / "rootfs.ext4"
    if raw.stat().st_size != images["images"][raw.name]["bytes"]:
        raise SystemExit("Raw rootfs size changed after image validation")
else:
    sparse = out / "rootfs.img"
    if file_sha256(sparse) != images["images"][sparse.name]["sha256"]:
        raise SystemExit("Sparse rootfs changed after image validation")
print("Package inputs match current validated boot/rootfs")
