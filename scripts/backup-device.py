#!/usr/bin/env python3
"""Read and verify the connected Gemini's boot/recovery partitions over ADB."""
import base64
import datetime
import hashlib
import json
import pathlib
import re
import subprocess

script_directory = pathlib.Path(__file__).resolve().parent
root = script_directory.parent if script_directory.name == "scripts" else script_directory
directory = root / "inventory" / ("local-backup-" + datetime.date.today().isoformat())
directory.mkdir(parents=True, exist_ok=True)


def adb(*arguments):
    return subprocess.run(["adb", *arguments], check=True, capture_output=True).stdout


devices = [line.split()[0] for line in adb("devices").decode().splitlines()
           if len(line.split()) == 2 and line.split()[1] == "device"]
if len(devices) != 1:
    raise SystemExit("Connect exactly one authorized Android device")
if adb("shell", "getprop ro.product.device").decode().strip() != "gemini":
    raise SystemExit("Connected device is not gemini")
metadata = {"device": "gemini", "serial": devices[0], "partitions": {}}
aboot_info = adb("shell", "su -c 'sha256sum /dev/block/bootdevice/by-name/aboot'").decode()
aboot_digest = re.search(r"\b([0-9a-f]{64})\b", aboot_info)
if not aboot_digest:
    raise SystemExit("Could not identify the installed aboot firmware")
metadata["aboot_sha256"] = aboot_digest.group(1)
for name in ("boot", "recovery"):
    device = "/dev/block/bootdevice/by-name/" + name
    info = adb("shell", f"su -c 'blockdev --getsize64 {device}; sha256sum {device}'").decode()
    size = re.search(r"^([0-9]+)\s*$", info, re.M)
    digest = re.search(r"\b([0-9a-f]{64})\b", info)
    if not size or not digest:
        raise SystemExit("Could not read partition metadata for " + name)
    size, digest = int(size.group(1)), digest.group(1)
    output = directory / (name + "-android.img")
    if output.is_file() and output.stat().st_size == size:
        with output.open("rb") as stream:
            valid_existing = hashlib.file_digest(stream, "sha256").hexdigest() == digest
    else:
        valid_existing = False
    if not valid_existing:
        # ASCII transfer avoids Magisk/PTY newline translation corrupting binary
        # output. The decoded result must still match the hash read on the phone.
        encoded = adb("exec-out", "su", "-c", "base64 " + device)
        data = base64.b64decode(encoded)
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise SystemExit("Transfer hash mismatch for " + name)
        temporary = output.with_suffix(".img.partial")
        temporary.write_bytes(data)
        temporary.replace(output)
    metadata["partitions"][name] = {"bytes": size, "sha256": digest, "file": output.name}
    print(f"Verified {name}: {size:,} bytes, SHA256 {digest}", flush=True)
(directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
print("Read-only device backup:", directory)
