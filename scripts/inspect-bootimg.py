#!/usr/bin/env python3
"""Validate the boot header, kernel config, DTB, init and dependency closure."""
import argparse
import gzip
import hashlib
import json
import pathlib
import platform
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import zlib
from boot_layout import parse_boot_image, PROFILE
from wifi_board import TARGET as WIFI_BOARD_TARGET, validate as validate_wifi_board

parser = argparse.ArgumentParser()
parser.add_argument("image", type=pathlib.Path)
parser.add_argument("--mode", choices=["production", "diagnostic"], required=True)
parser.add_argument("--require-server-config", action="store_true")
parser.add_argument("--report", type=pathlib.Path)
args = parser.parse_args()
project = pathlib.Path(__file__).resolve().parents[1]
blob = args.image.read_bytes()
assert 48 <= len(blob) <= 64 * 1024 * 1024, "Boot image is empty or larger than 64 MiB"
magic, kernel_size, kernel_address, ramdisk_size, ramdisk_address, _, _, tags, page, version = struct.unpack_from("<8s9I", blob)
image, dtb, ramdisk, memory_layout = parse_boot_image(blob)
ramdisk_offset = page + (kernel_size + page - 1) // page * page
kernel = blob[page:page + kernel_size]
ramdisk = blob[ramdisk_offset:ramdisk_offset + ramdisk_size]
assert len(kernel) == kernel_size and len(ramdisk) == ramdisk_size, "Truncated boot payload"
start = image.index(b"IKCFG_ST") + 8
end = image.index(b"IKCFG_ED", start)
config = gzip.decompress(image[start:end])
archive = gzip.decompress(ramdisk)
entries, entry_modes, position = {}, {}, 0
while position + 110 <= len(archive):
    assert archive[position:position + 6] == b"070701", "Invalid newc archive"
    fields = [int(archive[position + 6 + n * 8:position + 14 + n * 8], 16) for n in range(13)]
    size, name_size = fields[6], fields[11]
    name = archive[position + 110:position + 110 + name_size - 1].decode().removeprefix("./")
    position = (position + 110 + name_size + 3) & ~3
    data = archive[position:position + size]
    assert len(data) == size, "Truncated CPIO file"
    position = (position + size + 3) & ~3
    if name == "TRAILER!!!":
        break
    assert not name.startswith("/") and ".." not in pathlib.PurePosixPath(name).parts, "Unsafe archive path"
    assert fields[2:4] == [0, 0], "Initramfs file is not root-owned"
    entries[name] = data
    entry_modes[name] = fields[1]
else:
    raise AssertionError("Missing CPIO trailer")
assert "dev/console" in entries and "bin/busybox" in entries and "init" in entries
assert WIFI_BOARD_TARGET in entries, "Mi 5-specific Wi-Fi board data missing from early firmware"
wifi_board_sha256 = validate_wifi_board(entries[WIFI_BOARD_TARGET])
assert not any(name == "overlay" or name.startswith("overlay/") for name in entries), "Legacy deployment overlay is forbidden"
for name in ("init", "bin/busybox"):
    elf = entries[name]
    assert elf[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<H", elf, 18)[0] == 183, name + " is not ARM64"
    phoff = struct.unpack_from("<Q", elf, 32)[0]
    phsize, phcount = struct.unpack_from("<HH", elf, 54)
    assert all(struct.unpack_from("<I", elf, phoff + n * phsize)[0] != 3 for n in range(phcount)), name + " needs a dynamic loader"
metadata = json.loads(entries["usr/lib/gemini-initramfs.json"])
assert metadata["mode"] == args.mode, "Wrong initramfs mode"
assert metadata["init_source_sha256"] == hashlib.sha256((project / "initramfs/init.c").read_bytes()).hexdigest(), "Init source changed after packaging"
if args.mode == "diagnostic":
    assert b"No production rootfs will be selected or modified." in entries["init"]
    dependency_files = [name for name in entries if name.endswith("/modules.dep")]
    assert dependency_files, "Diagnostic module dependency index missing"
    for name in dependency_files:
        prefix = name.rsplit("/", 1)[0] + "/"
        for line in entries[name].decode().splitlines():
            module, dependencies = line.split(":", 1)
            for relative in [module, *dependencies.split()]:
                assert prefix + relative in entries, "Missing diagnostic module dependency: " + relative

with tempfile.TemporaryDirectory() as temporary:
    # A BusyBox symlink can exist even when that applet was disabled at build
    # time. Execute the packaged binary, rather than trusting the link list.
    busybox_path = pathlib.Path(temporary) / "busybox"
    busybox_path.write_bytes(entries["bin/busybox"])
    busybox_path.chmod(0o755)
    if platform.machine().lower() in ("aarch64", "arm64"):
        runner = []
    else:
        qemu = shutil.which("qemu-aarch64-static") or shutil.which("qemu-aarch64")
        if not qemu:
            raise SystemExit("Install qemu-user-static to validate packaged BusyBox applets")
        runner = [qemu]
    applets = set(subprocess.check_output(
        [*runner, str(busybox_path), "--list"], text=True, timeout=15).splitlines())
    missing_applets = sorted(pathlib.PurePosixPath(name).name
                             for name, data in entries.items()
                             if stat.S_ISLNK(entry_modes[name]) and data == b"busybox"
                             and pathlib.PurePosixPath(name).name not in applets)
    assert not missing_applets, "Packaged BusyBox lacks linked applets: " + ", ".join(missing_applets)
    dtb_path = pathlib.Path(temporary) / "gemini.dtb"
    dtb_path.write_bytes(dtb)
    compatible = subprocess.check_output(["fdtget", "-t", "s", str(dtb_path), "/", "compatible"], text=True)
    assert "xiaomi,gemini" in compatible, "DTB is not Gemini"
    boards = subprocess.check_output(["fdtget", "-t", "x", str(dtb_path), "/", "qcom,board-id"], text=True).split()
    assert ["20", "0"] in [boards[n:n + 2] for n in range(0, len(boards), 2)], "DTB does not cover board-id 32"
    charger_status = subprocess.run([
        "fdtget", "-t", "s", str(dtb_path),
        "/soc@0/spmi@400f000/pmic@2/charger@1000", "status"
    ], capture_output=True, text=True)
    charger_enabled = charger_status.stdout.strip() != "disabled"
    usb_supply = subprocess.run([
        "fdtget", "-t", "s", str(dtb_path),
        "/soc@0/usb@6af8800/usb@6a00000", "usb-psy-name"
    ], capture_output=True, text=True)
    if charger_enabled:
        assert usb_supply.returncode == 0 and usb_supply.stdout.strip() == "qcom-smbchg-usb", "DWC3 must route negotiated current to the charger"
    else:
        assert usb_supply.returncode != 0, "Minimal USB diagnostic must not wait for its disabled charger"
    assert b"CONFIG_USB_GADGET_VBUS_DRAW=500\n" in config, "USB gadget must request the configured 500 mA SDP budget"
    def cells(node, prop):
        return [int(value, 16) for value in subprocess.check_output(
            ["fdtget", "-t", "x", str(dtb_path), node, prop], text=True).split()]
    for cpu in range(4):
        zone = f"/thermal-zones/cpu{cpu}-thermal"
        policy_cpu = "cpu@0" if cpu < 2 else "cpu@100"
        expected = cells(f"/cpus/{policy_cpu}", "phandle")[0]
        trip = cells(zone + "/trips/trip-point0", "phandle")[0]
        assert cells(zone + "/cooling-maps/map-cpu", "cooling-device") == [expected, 4 if cpu < 2 else 8, 0xffffffff], "CPU cooling policy missing"
        assert cells(zone + "/cooling-maps/map-cpu", "trip") == [trip], "CPU cooling is not connected to its passive trip"
        assert cells(zone + "/trips/trip-point0", "temperature") == [65000], "Unexpected CPU passive temperature"
    nodes = subprocess.check_output(["fdtget", "-l", str(dtb_path), "/reserved-memory"], text=True).splitlines()
    for node in nodes:
        result = subprocess.run(["fdtget", "-t", "x", str(dtb_path), "/reserved-memory/" + node, "reg"], capture_output=True, text=True)
        if result.returncode:
            continue
        cells = [int(value, 16) for value in result.stdout.split()]
        for n in range(0, len(cells), 4):
            address, size = (cells[n] << 32) | cells[n + 1], (cells[n + 2] << 32) | cells[n + 3]
            for label, begin, end in (
                ('Kernel', memory_layout['kernel_address'], memory_layout['kernel_memory_end']),
                ('DTB', tags, tags + len(dtb)),
                ('Ramdisk', ramdisk_address, ramdisk_address + ramdisk_size),
            ):
                assert not (begin < address + size and address < end), label + " overlaps " + node
    if args.require_server_config:
        config_path = pathlib.Path(temporary) / "kernel.config"
        config_path.write_bytes(config)
        subprocess.run([sys.executable, str(project / "scripts/verify-kernel-config.py"), str(config_path)], check=True)
version_match = re.search(rb"Linux version ([^\s\x00]+)", image)
report = {"passed": True, "mode": args.mode, "image": str(args.image),
          "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
          "kernel_release": version_match.group(1).decode() if version_match else "unknown",
          "server_config_verified": args.require_server_config,
          "stock_lk_memory_verified": True, "bootloader_profile": PROFILE["name"],
          "usb_power_policy_verified": True,
          "cpu_thermal_cooling_maps_verified": True,
          "cpu_passive_temperature_millic": 65000,
          "cpu_minimum_cooling_states": {"little": 4, "big": 8},
          "usb_charger_enabled": charger_enabled,
          "memory_layout": memory_layout,
          "init_source_sha256": metadata["init_source_sha256"],
          "busybox_applets_verified": True,
          "wifi_board_sha256": wifi_board_sha256,
          "ramdisk_bytes": ramdisk_size, "archive_entries": len(entries)}
if args.report:
    args.report.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
