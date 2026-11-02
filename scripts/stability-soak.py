#!/usr/bin/env python3
"""Record and assess a bounded device soak; never reboot or tune hardware.

Run on the phone alongside tests/stability/workload.sh. Logs are private.
Elapsed acceptance time comes from uptime, not an initially incorrect RTC.
"""
import argparse
from datetime import datetime, timezone
import http.client
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

SERVICES = ("ssh", "NetworkManager", "docker", "mi5-console", "mi5-health.timer")
REQUIRED = {"boot_id", "uptime", "root_write_ok", "ext4_errors", "services", "failed_units",
            "charger_online", "usb_type", "battery", "battery_temp_c", "cpu_temp_c",
            "wifi_ipv4", "http_ok", "container_running", "container_oom", "container_restarts", "counter"}


def read(path):
    return Path(path).read_text().strip()


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=12,
                            env={**os.environ, "LC_ALL": "C"})
    if result.returncode:
        raise RuntimeError(f"{args[0]} returned {result.returncode}")
    return result.stdout


def verify_root_write(directory, value):
    # Host and device recorders can probe the same directory concurrently.
    with tempfile.NamedTemporaryFile(mode='w', dir=directory, prefix='write-probe-') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
        return read(stream.name) == value


def probe(directory, container="mi5-acceptance", port=18080):
    sample = {"timestamp": datetime.now(timezone.utc).isoformat(), "errors": []}
    try:
        sample["boot_id"] = read("/proc/sys/kernel/random/boot_id")
        sample["uptime"] = float(read("/proc/uptime").split()[0])
        battery = Path("/sys/class/power_supply/qcom-battery")
        sample["battery"] = int(read(battery / "capacity"))
        sample["battery_temp_c"] = int(read(battery / "temp")) / 10
        sample["battery_current_ua"] = int(read(battery / "current_now"))
        sample["usb_type"] = read("/sys/class/power_supply/qcom-smbchg-usb/usb_type")
        sample["charger_online"] = read("/sys/class/power_supply/qcom-smbchg-usb/online") == "1"
        cpu = [int(read(p / "temp")) / 1000 for p in Path("/sys/class/thermal").glob("thermal_zone*")
               if read(p / "type").startswith("cpu")]
        sample["cpu_temp_c"] = max(cpu)
        device = Path(f"/sys/dev/block/{os.major(os.stat('/').st_dev)}:{os.minor(os.stat('/').st_dev)}").resolve().name
        sample["ext4_errors"] = int(read(f"/sys/fs/ext4/{device}/errors_count"))
        # Mount flags alone missed emergency_ro during the original failure.
        sample["root_write_ok"] = verify_root_write(directory, sample["boot_id"])
        states = subprocess.run(["systemctl", "is-active", *SERVICES], capture_output=True,
                                text=True, timeout=12).stdout.splitlines()
        sample["services"] = dict(zip(SERVICES, states))
        failed = run("systemctl", "--failed", "--no-legend", "--plain", "--no-pager")
        sample["failed_units"] = [line.split()[0] for line in failed.splitlines() if line.strip()]
        addresses = json.loads(run("ip", "-j", "-4", "addr", "show", "dev", "wlan0"))
        sample["wifi_ipv4"] = any(a.get("scope") == "global" for d in addresses for a in d.get("addr_info", []))
        details = json.loads(run("docker", "inspect", container))[0]
        sample["container_running"] = details["State"]["Running"]
        sample["container_oom"] = details["State"]["OOMKilled"]
        sample["container_restarts"] = details["RestartCount"]
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            connection.request("GET", "/")
            response = connection.getresponse()
            body = json.loads(response.read(4096))
            if not isinstance(body, dict):
                raise ValueError("HTTP response must be a JSON object")
            sample["http_ok"] = response.status == 200 and body.get("workload") == "mi5-acceptance"
            sample["counter"] = body["counter"]
        finally:
            connection.close()
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, subprocess.TimeoutExpired,
            http.client.HTTPException) as exc:
        sample["errors"].append(type(exc).__name__ + ": " + str(exc))
    return sample


def assess(samples, hours=24):
    if not math.isfinite(hours) or hours <= 0:
        raise ValueError("Duration must be positive and finite")
    failures = []
    elapsed = 0
    complete = [s for s in samples if REQUIRED.issubset(s)]
    if samples:
        first = complete[0] if complete else {}
        previous = first
        for number, sample in enumerate(samples):
            if not REQUIRED.issubset(sample):
                # An unreachable SSH endpoint gives no observation of storage,
                # temperature or power. Fail coverage without inventing faults.
                failures.append({"sample": number, "reasons": ["probe unavailable or incomplete"],
                                 "errors": sample.get("errors", []),
                                 "missing_fields": sorted(REQUIRED.difference(sample))})
                continue
            reasons = []
            if sample.get("errors"):
                reasons.append("probe error")
            if not sample.get("boot_id") or sample.get("boot_id") != first.get("boot_id"):
                reasons.append("unexpected reboot or missing boot ID")
            gap = sample.get("uptime", -1) - previous.get("uptime", 0)
            if gap < 0 or gap > 180:
                reasons.append("sampling gap or uptime reversal")
            if not sample.get("root_write_ok") or sample.get("ext4_errors") != 0:
                reasons.append("storage error")
            if any(sample.get("services", {}).get(name) != "active" for name in SERVICES):
                reasons.append("required service inactive")
            if sample.get("failed_units"):
                reasons.append("failed systemd unit")
            if not sample.get("charger_online") or "[DCP]" not in sample.get("usb_type", ""):
                reasons.append("DCP charger absent")
            if not 15 <= sample.get("battery", -1) <= 100:
                reasons.append("battery outside acceptance range")
            if not 0 <= sample.get("battery_temp_c", 100) <= 43:
                reasons.append("battery temperature outside acceptance range")
            if not 0 <= sample.get("cpu_temp_c", 100) < 85:
                reasons.append("CPU temperature outside acceptance range")
            if not sample.get("wifi_ipv4") or not sample.get("http_ok"):
                reasons.append("network or HTTP unavailable")
            if not sample.get("container_running") or sample.get("container_oom"):
                reasons.append("container stopped or OOM")
            if sample.get("container_restarts", -1) != first.get("container_restarts", -2):
                reasons.append("container restart count changed")
            counter = sample.get("counter")
            previous_counter = previous.get("counter", 0)
            if type(previous_counter) is not int:
                previous_counter = 0
            if type(counter) is not int or counter < previous_counter:
                reasons.append("persistent counter invalid or reversed")
            if reasons:
                failures.append({"sample": number, "reasons": reasons})
            previous = sample
        last = complete[-1] if complete else {}
        elapsed = max(0, last.get("uptime", 0) - first.get("uptime", 0))
        if complete and last["battery"] < first["battery"] - 3:
            failures.append({"sample": len(samples) - 1, "reasons": ["battery declined on charger"]})
        first_counter, last_counter = first.get("counter"), last.get("counter")
        if (elapsed >= 180 and type(first_counter) is int and type(last_counter) is int
                and last_counter <= first_counter):
            failures.append({"sample": len(samples) - 1, "reasons": ["application counter did not advance"]})
    enough = elapsed >= hours * 3600 and len(complete) >= math.ceil(hours * 3600 / 120) + 1
    return {"status": "failed" if failures else "passed" if enough else "running",
            "required_hours": hours, "elapsed_seconds": elapsed,
            "samples": len(samples), "complete_samples": len(complete), "failures": failures,
            "scope": "Local device/charger/app soak; independent Wi-Fi reachability and other release gates are separate"}


def load_samples(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def record(directory):
    config = json.loads((directory / "run.json").read_text())
    if not 0 < config["hours"] <= 48:
        raise ValueError("Record duration must be within 48 hours")
    path = directory / "samples.jsonl"
    samples = load_samples(path)
    if len(samples) >= 3000 or (samples and assess(samples, config["hours"])["status"] != "running"):
        subprocess.run(["systemctl", "stop", "mi5-acceptance.timer"], timeout=12, check=False)
        return
    samples.append(probe(directory, config.get("container", "mi5-acceptance"), config.get("port", 18080)))
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps(samples[-1], sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    report = assess(samples, config["hours"])
    temporary = directory / "report.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(directory / "report.json")
    if report["status"] != "running":
        # This timer belongs only to the acceptance run; do not leave a
        # finished/failed test polling forever or change any server service.
        subprocess.run(["systemctl", "stop", "mi5-acceptance.timer"], timeout=12, check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("probe", "record", "report"))
    parser.add_argument("path", type=Path, help="Private state directory, or JSONL file for report")
    parser.add_argument("--hours", type=float, default=24)
    args = parser.parse_args()
    if args.mode == "probe":
        print(json.dumps(probe(args.path), sort_keys=True))
    elif args.mode == "record":
        record(args.path)
    else:
        report = assess(load_samples(args.path), args.hours)
        print(json.dumps(report, indent=2))
        return {"passed": 0, "failed": 1, "running": 2}[report["status"]]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
