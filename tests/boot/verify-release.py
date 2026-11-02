#!/usr/bin/env python3
"""Read finished release archives; never invoke ADB, fastboot or an installer."""
import argparse
import configparser
import hashlib
import json
import pathlib
import tarfile
import zipfile
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
from project_metadata import artifact_names
from wifi_board import TARGET as WIFI_BOARD_TARGET, validate as validate_wifi_board
NAMES = artifact_names()

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=pathlib.Path)
args = parser.parse_args()
out = args.output


def sums(data):
    return {name.lstrip("*"): digest for digest, name in
            (line.split(maxsplit=1) for line in data.decode().splitlines())}


def digest_stream(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


class HashReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        data = self.stream.read(size)
        self.digest.update(data)
        return data


report = {"passed": False, "hardware_boot_verified": False}
with zipfile.ZipFile(out / NAMES["fastboot"]) as archive:
    expected = sums(archive.read("SHA256SUMS"))
    image = json.loads((out / "rootfs-image-validation.json").read_text())
    for name in ("boot.img", "rootfs.img"):
        with archive.open(name) as stream:
            actual = digest_stream(stream)
        assert actual == expected[name], f"Fastboot ZIP checksum mismatch: {name}"
        if name == "rootfs.img":
            assert actual == image["images"][name]["sha256"]
        else:
            assert actual == json.loads((out / "boot-validation.json").read_text())["sha256"]
    for name in ("install.py", "backup-device.py", "boot_layout.py", "gemini-lk.json", "flash-all.sh", "flash-all.bat", "README.txt"):
        assert archive.read(name), f"Missing Fastboot helper: {name}"
    project = pathlib.Path(__file__).resolve().parents[2]
    for name, source in {
        "install.py": "scripts/fastboot-install.py",
        "backup-device.py": "scripts/backup-device.py",
        "boot_layout.py": "scripts/boot_layout.py",
        "gemini-lk.json": "config/gemini-lk.json",
    }.items():
        assert archive.read(name) == (project / source).read_bytes(), f"Stale Fastboot helper: {name}"
    report["fastboot_helpers_current"] = True
    report["fastboot_payload_checksums"] = True

with zipfile.ZipFile(out / NAMES["twrp"]) as archive:
    expected = sums(archive.read("SHA256SUMS"))
    for name in ("boot.img", "rootfs-min-bytes", "bootloader-sha256"):
        assert hashlib.sha256(archive.read(name)).hexdigest() == expected[name], name
    assert int(archive.read("rootfs-min-bytes")) == image["images"]["rootfs.ext4"]["bytes"]
    profile = json.loads((pathlib.Path(__file__).resolve().parents[2] / 'config/gemini-lk.json').read_text())
    assert archive.read('bootloader-sha256').decode().strip() == profile['aboot_sha256']
    assert archive.read("META-INF/com/google/android/update-binary").startswith(b"#!/sbin/sh")
    marker, entries, critical = None, 0, set()
    priority_verified, watchdog_masked = False, False
    wifi_mac_policy_verified = False
    server_files = set()
    server_masks = set()
    wifi_board_verified = False
    with archive.open("rootfs.tar.gz") as compressed:
        hashed = HashReader(compressed)
        with tarfile.open(fileobj=hashed, mode="r|gz") as rootfs:
            for entry in rootfs:
                name = entry.name.removeprefix("./")
                assert not name.startswith("/") and ".." not in pathlib.PurePosixPath(name).parts
                assert not (name.startswith("etc/ssh/ssh_host_") and name.endswith("_key"))
                assert pathlib.PurePosixPath(name).name != "authorized_keys"
                assert name != 'var/lib/NetworkManager/secret_key', 'Builder NetworkManager identity shipped'
                if name in ("etc/shadow", "etc/gemini-rootfs", "usr/lib/systemd/systemd"):
                    assert entry.uid == 0, f"Wrong owner in rootfs tar: {name}"
                    critical.add(name)
                if name == "etc/gemini-rootfs":
                    marker = rootfs.extractfile(entry).read()
                if name == WIFI_BOARD_TARGET:
                    assert entry.isfile() and entry.uid == entry.gid == 0
                    validate_wifi_board(rootfs.extractfile(entry).read())
                    wifi_board_verified = True
                if name == "etc/NetworkManager/conf.d/20-gemini-priority.conf":
                    priority = configparser.ConfigParser()
                    priority.read_string(rootfs.extractfile(entry).read().decode())
                    wifi_mac_policy_verified = priority.get('connection-wifi', 'wifi.cloned-mac-address', fallback='') == 'stable'
                    priority_verified = all(priority.get(section, family + ".route-metric") == metric
                                            for section, metric in (("connection-wifi", "100"),
                                                                    ("connection-ethernet", "600"))
                                            for family in ("ipv4", "ipv6"))
                if name == "etc/systemd/system/mi5-network-watchdog.service":
                    watchdog_masked = entry.issym() and entry.linkname == "/dev/null"
                wanted = {
                    "usr/local/sbin/gemini-server-mode.sh",
                    "usr/local/sbin/gemini-thermal-source.sh",
                    "etc/systemd/system/gemini-server-mode.service",
                    "etc/systemd/system/armbian-hardware-monitor.service.d/20-gemini-cpu-temperature.conf",
                    "etc/systemd/system/console-setup.service.d/20-gemini-tmpfiles.conf",
                    "usr/local/lib/mi5/console.py", "usr/local/lib/mi5/usb_gadget.py",
                    "usr/local/lib/mi5/wifi_ready.py",
                    "etc/systemd/system/mi5-wifi-ready.service",
                    "etc/systemd/system/NetworkManager.service.d/20-mi5-wifi-ready.conf",
                    "etc/systemd/system/NetworkManager-wait-online.service.d/20-mi5-startup.conf",
                    "usr/local/sbin/mi5-config",
                    "etc/default/mi5-console", "etc/default/mi5-usb",
                    "etc/systemd/logind.conf.d/20-mi5-console.conf",
                    "etc/systemd/system/mi5-console.service",
                    "etc/systemd/system/mi5-usb-gadget.service",
                    "etc/systemd/system/mi5-usb-dhcp.service",
                    "usr/lib/sysusers.d/mi5-usb.conf",
                    "etc/NetworkManager/conf.d/99-usb-gadget.conf",
                }
                if name in wanted:
                    source = pathlib.Path(__file__).resolve().parents[2] / "rootfs-overlay" / name
                    assert entry.isfile() and entry.uid == entry.gid == 0, name
                    assert rootfs.extractfile(entry).read() == source.read_bytes(), name
                    server_files.add(name)
                if name.startswith("etc/systemd/system/plymouth-") and name.endswith(".service"):
                    if entry.issym() and entry.linkname == "/dev/null":
                        server_masks.add(pathlib.PurePosixPath(name).name)
                entries += 1
        while hashed.read(4 * 1024 * 1024):
            pass
        assert hashed.digest.hexdigest() == expected["rootfs.tar.gz"]
    assert marker == b"gemini-rootfs-v1\n"
    assert critical == {"etc/shadow", "etc/gemini-rootfs", "usr/lib/systemd/systemd"}
    assert priority_verified, "TWRP rootfs does not prefer Wi-Fi over LAN"
    assert wifi_mac_policy_verified, "TWRP rootfs can use the shared board-template MAC"
    assert wifi_board_verified, "TWRP rootfs lacks verified Mi 5 Wi-Fi board data"
    assert watchdog_masked, "TWRP rootfs can still cycle the primary Wi-Fi radio"
    assert server_files == wanted, "TWRP rootfs is missing LCD/USB server helpers"
    assert {"plymouth-start.service", "plymouth-quit.service", "plymouth-quit-wait.service",
            "plymouth-reboot.service", "plymouth-halt.service", "plymouth-poweroff.service",
            "plymouth-kexec.service"} <= server_masks
    report["server_console_usb_files_verified"] = True
    report["wifi_primary_policy_verified"] = True
    report["stable_wifi_mac_policy_verified"] = True
    report["wifi_board_verified"] = True
    report["legacy_radio_watchdog_masked"] = True
    report["twrp_payload_checksums"] = True
    report["twrp_rootfs_tar_entries"] = entries
    report["twrp_rootfs_compressed_bytes"] = archive.getinfo("rootfs.tar.gz").file_size
    report["twrp_staged_payload_bytes"] = sum(archive.getinfo(name).file_size for name in
                                              ("rootfs.tar.gz", "boot.img", "SHA256SUMS", "rootfs-min-bytes", "bootloader-sha256"))

report["passed"] = True
(out / "release-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
