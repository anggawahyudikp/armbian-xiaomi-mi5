#!/usr/bin/env python3
"""Gemini installer: finish every preflight check before the first flash."""
import argparse
import hashlib
import json
import pathlib
import re
import shutil
import struct
import subprocess
import sys
from boot_layout import parse_boot_image, PROFILE


def expanded_size(path):
    with path.open("rb") as image:
        header = image.read(28)
    if len(header) >= 28 and struct.unpack_from("<I", header)[0] == 0xED26FF3A:
        _, major, _, file_header, chunk_header, block_size, blocks, _, _ = struct.unpack("<I4H4I", header)
        if major != 1 or file_header < 28 or chunk_header < 12 or block_size == 0:
            raise ValueError("Invalid Android sparse image header")
        return block_size * blocks
    return path.stat().st_size


def validate_payloads(directory):
    files = [directory / "boot.img", directory / "rootfs.img"]
    for path in files:
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing or empty payload: {path.name}")
    checksums = {}
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        checksums[name.lstrip("*")] = digest
    for path in files:
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if checksums.get(path.name) != digest:
            raise ValueError(f"Checksum mismatch: {path.name}")
    parse_boot_image(files[0].read_bytes())
    return files[0].stat().st_size, expanded_size(files[1])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    parser.add_argument("--serial")
    parser.add_argument("--device-proof", type=pathlib.Path,
                        help="Required metadata.json from backup-device.py: same Gemini serial and supported aboot hash")
    parser.add_argument("--yes", action="store_true", help="Explicitly authorize erasing Android userdata")
    args = parser.parse_args(argv)
    directory = args.directory.resolve()
    boot_bytes, root_bytes = validate_payloads(directory)
    fastboot = shutil.which("fastboot")
    if not fastboot:
        raise ValueError("Install Android platform-tools and put fastboot in PATH")

    def invoke(options, required=True):
        if "flash" in options:
            # Large sparse writes can take minutes. Preserve fastboot progress
            # while keeping preflight output available for validation below.
            with subprocess.Popen([fastboot, *options], stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True,
                                  bufsize=1) as process:
                for line in process.stdout:
                    print(line, end="", flush=True)
                code = process.wait()
            if required and code:
                raise ValueError(f"fastboot flash failed with exit status {code}; see progress above")
            return code, ""
        result = subprocess.run([fastboot, *options], capture_output=True, text=True)
        output = result.stdout + result.stderr
        if required and result.returncode:
            raise ValueError("fastboot failed: " + " ".join(options) + "\n" + output)
        return result.returncode, output

    _, version = invoke(["--version"])
    match = re.search(r"fastboot version (\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (37, 0, 1):
        raise ValueError("Use Android SDK Platform-Tools fastboot 37.0.1 or newer. "
                         "Older 34.0.5 stalled during this device's large-image installation; "
                         "no partitions have been changed.")
    print(version.strip(), flush=True)
    _, listing = invoke(["devices"])
    devices = [line.split()[0] for line in listing.splitlines()
               if len(line.split()) >= 2 and line.split()[1] == "fastboot"]
    if args.serial:
        if args.serial not in devices:
            raise ValueError("Selected serial is not connected in fastboot mode")
        serial = args.serial
    elif len(devices) == 1:
        serial = devices[0]
    else:
        raise ValueError("Connect exactly one fastboot device, or select --serial")
    prefix = ["-s", serial]

    def getvar(name):
        _, output = invoke([*prefix, "getvar", name])
        match = re.search(re.escape(name) + r":\s*(\S+)", output)
        if not match:
            raise ValueError(f"fastboot did not return {name}")
        return match.group(1)

    product = getvar("product")
    if product not in ("gemini", "MSM8996"):
        raise ValueError(f"Product {product!r} is not a supported Gemini bootloader")
    proof = json.loads(args.device_proof.read_text()) if args.device_proof else {}
    if not (proof.get("device") == "gemini" and proof.get("serial") == serial
            and proof.get("aboot_sha256") == PROFILE["aboot_sha256"]):
        raise ValueError("Supply --device-proof metadata.json from backup-device.py for this same "
                         "Gemini serial and the supported aboot hash; LK load addresses are firmware-specific")
    _, unlocked = invoke([*prefix, "getvar", "unlocked"], required=False)
    if not re.search(r"unlocked:\s*(?:yes|true|1)\b", unlocked, re.I):
        _, unlocked = invoke([*prefix, "oem", "device-info"], required=False)
        if not re.search(r"Device unlocked:\s*true\b", unlocked, re.I):
            raise ValueError("Bootloader unlock was not confirmed; userdata has not been touched")
    for name, size in (("boot", boot_bytes), ("userdata", root_bytes)):
        value = getvar("partition-size:" + name)
        available = int(value, 16)
        if size <= 0 or size > available:
            raise ValueError(f"{name} payload {size} bytes does not fit partition {available} bytes")
    value = getvar("max-download-size")
    if not re.fullmatch(r"(?:0[xX][0-9a-fA-F]+|[0-9]+)", value):
        raise ValueError("Bootloader returned an invalid max-download-size")
    maximum_download = int(value, 16 if value.lower().startswith("0x") else 10)
    if not 0 < maximum_download <= 0xffffffff:
        raise ValueError("Bootloader max-download-size is outside the fastboot transfer range")
    if boot_bytes > maximum_download:
        raise ValueError(f"Boot payload {boot_bytes} bytes exceeds max-download-size "
                         f"{maximum_download}; refusing to sparse-flash the boot image")
    transfer_limit = min(256 * 1024 * 1024, maximum_download)
    transfer_argument = "64M" if transfer_limit == 64 * 1024 * 1024 else str(transfer_limit)
    print(f"Verified gemini ({serial}); boot {boot_bytes:,} bytes, expanded rootfs {root_bytes:,} bytes.")
    print(f"Verified bootloader download limit {maximum_download:,} bytes; "
          f"userdata transfer cap {transfer_limit:,} bytes.")
    print("This will ERASE ALL Android userdata and replace the boot partition.")
    if not args.yes and input("Type ERASE ANDROID to continue: ").strip() != "ERASE ANDROID":
        print("Aborted; no partitions changed.")
        return 0
    for partition, filename in (("userdata", "rootfs.img"), ("boot", "boot.img")):
        print(f"Flashing {partition}...", flush=True)
        _, output = invoke([*prefix, "-S", transfer_argument, "flash", partition, str(directory / filename)])
        print(output, end="")
    invoke([*prefix, "reboot"])
    print("Flash complete. Armbian first-login setup will create your user.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, EOFError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise SystemExit(1)
