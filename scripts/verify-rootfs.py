#!/usr/bin/env python3
"""Run ARM64 userspace smoke checks and validate the shipped module metadata."""
import argparse
import configparser
import json
import pathlib
import re
import runpy
import shutil
import subprocess
import sys
from artifact_identity import tree_sha256
from rootfs_service_policy import is_build_stub
from wifi_board import TARGET as WIFI_BOARD_TARGET, validate as validate_wifi_board

parser = argparse.ArgumentParser()
parser.add_argument("rootfs", type=pathlib.Path)
parser.add_argument("--kernel-release", required=True)
parser.add_argument("--report", type=pathlib.Path)
args = parser.parse_args()
root = args.rootfs.resolve()
errors, checks = [], []


def check(name, passed, detail=""):
    checks.append({"name": name, "passed": bool(passed), "detail": detail})
    if not passed:
        errors.append(name + (": " + detail if detail else ""))


marker = root / "etc/gemini-rootfs"
check("Build-only service-start blocker removed", not is_build_stub(root / "usr/sbin/policy-rc.d"))
check("Gemini rootfs marker", marker.is_file() and marker.read_text() == "gemini-rootfs-v1\n")
release = root / "etc/armbian-release"
check("Armbian metadata", release.is_file())
serial_dropins = list((root / "etc/systemd/system/serial-getty@.service.d").glob("*.conf"))
serial_dropins += list((root / "etc/systemd/system/serial-getty@ttyGS0.service.d").glob("*.conf"))
check("USB console requires authentication",
      all("--autologin" not in p.read_text() for p in serial_dropins))
packages = {}
for stanza in (root / "var/lib/dpkg/status").read_text().split("\n\n"):
    fields = dict(re.findall(r"^([A-Za-z-]+): (.*)$", stanza, re.M))
    if fields.get("Status") == "install ok installed":
        packages[fields["Package"]] = fields
check("Armbian Gemini BSP installed", "armbian-bsp-cli-gemini-edge" in packages)
check("Armbian base-files installed", "Armbian-Original-Hash" in packages.get("base-files", {}))
check("Genuine armbian-config installed", "armbian-config" in packages)
try:
    check("Mi 5-specific Wi-Fi board data", True,
          validate_wifi_board((root / WIFI_BOARD_TARGET).read_bytes()))
except (OSError, ValueError) as exc:
    check("Mi 5-specific Wi-Fi board data", False, str(exc))

qemu = shutil.which("qemu-aarch64-static")
if not qemu:
    raise SystemExit("Install qemu-user-static to validate ARM64 userspace")
programs = {
    "locale": ("usr/bin/locale", ["-a"]),
    "bash": ("usr/bin/bash", ["-c", "printf 'bash-ok\\n'"]),
    "systemd": ("usr/lib/systemd/systemd", ["--version"]),
    "NetworkManager": ("usr/sbin/NetworkManager", ["--version"]),
    "nmcli": ("usr/bin/nmcli", ["--version"]),
    "wpa_supplicant": ("usr/sbin/wpa_supplicant", ["-v"]),
    "iw": ("usr/sbin/iw", ["--version"]),
    "rfkill": ("usr/sbin/rfkill", ["--version"]),
    "sshd": ("usr/sbin/sshd", ["-V"]),
    "busybox": ("usr/bin/busybox", ["true"]),
}
for name, (relative, options) in programs.items():
    executable = root / relative
    if name == "busybox" and not executable.is_file():
        executable = root / "bin/busybox"
    try:
        result = subprocess.run([qemu, "-L", str(root), str(executable), *options],
                                capture_output=True, text=True, timeout=30)
        check("ARM64 " + name, result.returncode == 0,
              (result.stdout + result.stderr).strip()[:1500])
        if name == "locale":
            check("English UTF-8 locale generated", "en_US.utf8" in result.stdout.splitlines())
    except (OSError, subprocess.TimeoutExpired) as exc:
        check("ARM64 " + name, False, str(exc))

# Ask the actual target NetworkManager to merge its shipped configuration.
# --print-config never starts a daemon or changes the build host's network.
try:
    result = subprocess.run(["chroot", str(root), "/usr/sbin/NetworkManager", "--print-config"],
                            capture_output=True, text=True, timeout=30)
    effective = configparser.ConfigParser(interpolation=None)
    effective.read_string(result.stdout)
    check("Stable Wi-Fi identity generated on the installed system",
          result.returncode == 0
          and effective.get('connection-wifi', 'wifi.cloned-mac-address', fallback='') == 'stable'
          and not (root / 'var/lib/NetworkManager/secret_key').exists())
    expected = {"connection-wifi": ("type:wifi", "100"),
                "connection-ethernet": ("type:ethernet", "600")}
    for section, (device, metric) in expected.items():
        check("Network priority " + section,
              result.returncode == 0 and effective.get(section, "match-device", fallback="") == device
              and all(effective.get(section, family + ".route-metric", fallback="") == metric
                      for family in ("ipv4", "ipv6")), result.stderr.strip())
except (OSError, subprocess.TimeoutExpired, configparser.Error) as exc:
    check("NetworkManager effective priority configuration", False, str(exc))
watchdog_mask = root / "etc/systemd/system/mi5-network-watchdog.service"
check("Legacy radio-cycling watchdog masked", watchdog_mask.is_symlink()
      and watchdog_mask.readlink() == pathlib.Path("/dev/null"))
thermal_dropin = root / "etc/systemd/system/armbian-hardware-monitor.service.d/20-gemini-cpu-temperature.conf"
check("CPU temperature selected instead of battery",
      thermal_dropin.is_file()
      and "ExecStartPost=/usr/local/sbin/gemini-thermal-source.sh" in thermal_dropin.read_text()
      and (root / "usr/local/sbin/gemini-thermal-source.sh").is_file())
server_link = root / "etc/systemd/system/multi-user.target.wants/gemini-server-mode.service"
check("Server profile with LCD console enabled",
      server_link.is_symlink() and server_link.readlink() == pathlib.Path("../gemini-server-mode.service")
      and (root / "usr/local/sbin/gemini-server-mode.sh").is_file()
      and (root / "etc/systemd/system/multi-user.target.wants/mi5-console.service").is_symlink()
      and (root / "usr/local/lib/mi5/console.py").is_file()
      and all((root / f"etc/systemd/system/{service}.service").is_symlink()
              and (root / f"etc/systemd/system/{service}.service").readlink() == pathlib.Path("/dev/null")
              for service in ("plymouth-start", "plymouth-quit", "plymouth-quit-wait"))
      and not any((root / f"etc/systemd/system/{target}.target.wants/{service}.service").is_symlink()
                  for target in ("multi-user", "graphical") for service in ("display-unblank", "gemini-fb-ui")))
check("USB management service and DHCP package",
      "dnsmasq-base" in packages
      and all((root / f"etc/systemd/system/multi-user.target.wants/{name}.service").is_symlink()
              for name in ("mi5-usb-gadget", "mi5-usb-dhcp"))
      and (root / "usr/local/lib/mi5/usb_gadget.py").is_file())
try:
    usb = runpy.run_path(str(root / "usr/local/lib/mi5/usb_gadget.py"))
    descriptors = {mode: usb["device_descriptor_values"](mode) for mode in ("rndis", "ncm")}
    cache_keys = [tuple(int(item[key], 0) for key in ("idVendor", "idProduct", "bcdDevice"))
                  for item in descriptors.values()]
    check("USB modes have separate Windows OS descriptor caches",
          len(set(cache_keys)) == 2 and all(key[2] != 0x0101 for key in cache_keys),
          json.dumps({mode: item["bcdDevice"] for mode, item in descriptors.items()}))
except Exception as exc:
    check("USB modes have separate Windows OS descriptor caches", False, str(exc))
check("Power key controls LCD without suspending server",
      "HandlePowerKey=ignore" in (root / "etc/systemd/logind.conf.d/20-mi5-console.conf").read_text())
check("Shutdown splash cannot take over the server console",
      all((root / f"etc/systemd/system/plymouth-{action}.service").is_symlink()
          and (root / f"etc/systemd/system/plymouth-{action}.service").readlink() == pathlib.Path('/dev/null')
          for action in ('reboot', 'halt', 'poweroff', 'kexec')))
check("Bounded Wi-Fi enumeration before NetworkManager",
      (root / "etc/systemd/system/mi5-wifi-ready.service").is_file()
      and (root / "usr/local/lib/mi5/wifi_ready.py").is_file()
      and "After=mi5-wifi-ready.service" in (root / "etc/systemd/system/NetworkManager.service.d/20-mi5-wifi-ready.conf").read_text())
startup_wait = root / "etc/systemd/system/NetworkManager-wait-online.service.d/20-mi5-startup.conf"
check("Network startup allows a DHCP retry with a finite deadline",
      startup_wait.is_file()
      and "Environment=NM_ONLINE_TIMEOUT=120" in startup_wait.read_text()
      and "TimeoutStartSec=130" in startup_wait.read_text()
      and "ExecStart=" not in startup_wait.read_text())
check("Bounded health history and login diagnostics",
      (root / "usr/local/sbin/mi5-doctor").is_file()
      and (root / "etc/update-motd.d/80-mi5-health").is_file()
      and (root / "etc/systemd/system/timers.target.wants/mi5-health.timer").is_symlink()
      and "StateDirectoryMode=0700" in (root / "etc/systemd/system/mi5-health.service").read_text())
locale_config = root / "etc/default/locale"
login_locale = root / "etc/profile.d/99-mi5-language.sh"
ssh_locale = root / "etc/ssh/sshd_config.d/00-mi5-language.conf"
check("English system, login and SSH language policy",
      "LANG=en_US.UTF-8" in locale_config.read_text()
      and "LANGUAGE=en_US:en" in locale_config.read_text()
      and "export LC_ALL=en_US.UTF-8" in login_locale.read_text()
      and "SetEnv LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8" in ssh_locale.read_text())
console_dropin = root / "etc/systemd/system/console-setup.service.d/20-gemini-tmpfiles.conf"
check("Console setup follows boot temporary-file cleanup",
      console_dropin.is_file() and "After=systemd-tmpfiles-setup.service" in console_dropin.read_text())

builder_links = [str(path.relative_to(root))
                 for name in ("build", "source")
                 for path in (root / "usr/lib/modules").glob("*/" + name)
                 if path.is_symlink()]
check("No builder module links shipped", not builder_links, ", ".join(builder_links))

for name in ("msm", "panel_jdi_fhd_r63452", "zram"):
    result = subprocess.run(["modprobe", "-n", "-v", "-d", str(root), "-S", args.kernel_release, name],
                            capture_output=True, text=True)
    check("Module resolution " + name, result.returncode == 0, result.stdout + result.stderr)
check("Armbian ZRAM implementation installed", (root / "usr/lib/armbian/armbian-zram-config").is_file())
check("No local ZRAM implementation shadows Armbian", not (root / "usr/local/sbin/armbian-zram-config").exists())
resize_mask = root / "etc/systemd/system/armbian-resize-filesystem.service"
check("Generic partition resize masked", resize_mask.is_symlink() and resize_mask.readlink() == pathlib.Path("/dev/null"))
check("No SSH host keys shipped", not list((root / "etc/ssh").glob("ssh_host_*_key")))
keys = [str(p.relative_to(root)) for directory in ("root", "home")
        for p in (root / directory).rglob("authorized_keys")]
check("No builder authorized_keys shipped", not keys, ", ".join(keys))
check("Empty machine-id", (root / "etc/machine-id").read_bytes() == b"")
check("No personalized Wi-Fi profiles or health history shipped",
      not list((root / "etc/NetworkManager/system-connections").glob("*"))
      and not list((root / "var/lib/mi5-health").glob("*"))
      and not list((root / "run/mi5-wifi-recovery").glob("*")))
recovery_config = root / "etc/default/mi5-wifi-recovery"
check("Generic Wi-Fi recovery requires explicit opt-in",
      recovery_config.is_file() and "PROFILE_UUID=\n" in recovery_config.read_text()
      and not (root / "etc/systemd/system/timers.target.wants/mi5-wifi-recovery.timer").exists())
if args.report:
    args.report.write_text(json.dumps({"passed": not errors, "checks": checks,
                                      "kernel_release": args.kernel_release,
                                      "rootfs_sha256": tree_sha256(root) if not errors else None}, indent=2) + "\n")
for error in errors:
    print("FAIL:", error, file=sys.stderr)
if errors:
    raise SystemExit(1)
print(f"Rootfs validation passed: {len(checks)} checks")
