#!/usr/bin/env python3
"""Independently check Mi 5 SSH and HTTP from a Linux host during a soak.

Use normal SSH keys, or supply a local askpass helper. No passwords are accepted
on the command line or written into reports. This program never reboots a phone.
"""
import argparse
from datetime import datetime, timezone
import http.client
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

spec = importlib.util.spec_from_file_location("mi5_soak", Path(__file__).with_name("stability-soak.py"))
soak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soak)


def assess(samples, hours):
    report = soak.assess([s["probe"] for s in samples], hours)
    external_failures = [i for i, s in enumerate(samples) if not s.get("external_http_ok")]
    report["external_http_failures"] = external_failures
    if external_failures:
        report["status"] = "failed"
    report["scope"] = "Independent host SSH/HTTP plus device/charger/application soak; other release gates are separate"
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("target", help="SSH target, such as root@192.168.10.153")
    p.add_argument("--url", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--known-hosts", type=Path, required=True)
    p.add_argument("--askpass", type=Path)
    p.add_argument("--hours", type=float, default=24)
    p.add_argument("--interval", type=float, default=60)
    a = p.parse_args()
    if (a.target.startswith("-") or not 0 < a.hours <= 48 or not math.isfinite(a.hours)
            or not 10 <= a.interval <= 120):
        p.error("Use a valid SSH target, duration within 48 hours, and interval 10..120 seconds")
    a.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    a.output.chmod(0o700)
    if (a.output / "samples.jsonl").exists():
        p.error("Use a new output directory; do not overwrite an earlier run")
    env = os.environ.copy()
    ssh = ["ssh", "-T", "-o", "StrictHostKeyChecking=yes", "-o", "UserKnownHostsFile=" + str(a.known_hosts.resolve()),
           "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=8", "-o", "ServerAliveCountMax=1"]
    if a.askpass:
        env.update(SSH_ASKPASS=str(a.askpass.resolve()), SSH_ASKPASS_REQUIRE="force", DISPLAY=":99")
        ssh += ["-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no",
                "-o", "NumberOfPasswordPrompts=1"]
    else:
        ssh += ["-o", "BatchMode=yes"]
    ssh += [a.target, "python3 /opt/mi5-acceptance/probe.py probe /var/lib/mi5-acceptance"]
    metadata = {"started_at": datetime.now(timezone.utc).isoformat(), "hours": a.hours,
                "interval_seconds": a.interval, "target": a.target, "url": a.url,
                "pid": os.getpid()}
    (a.output / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (a.output / "run.json").chmod(0o600)
    start = time.monotonic()
    samples = []
    while True:
        cycle = time.monotonic()
        sample = {"host_elapsed": cycle - start, "external_http_ok": False}
        try:
            result = subprocess.run(ssh, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                    timeout=30, env=env)
            if result.returncode:
                raise RuntimeError("SSH returned " + str(result.returncode))
            sample["probe"] = json.loads(result.stdout)
            sample["ssh_seconds"] = time.monotonic() - cycle
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            sample["probe"] = {"errors": [type(exc).__name__ + ": " + str(exc)]}
        try:
            before = time.monotonic()
            with urllib.request.urlopen(a.url, timeout=5) as response:
                body = json.loads(response.read(4096))
                if not isinstance(body, dict):
                    raise ValueError("HTTP response must be a JSON object")
                sample["external_http_ok"] = (response.status == 200 and body.get("workload") == "mi5-acceptance"
                                              and type(body.get("counter")) is int)
                sample["external_counter"] = body.get("counter")
            sample["http_seconds"] = time.monotonic() - before
        except (OSError, ValueError, urllib.error.URLError, http.client.HTTPException) as exc:
            sample["http_error"] = type(exc).__name__ + ": " + str(exc)
        samples.append(sample)
        with os.fdopen(os.open(a.output / "samples.jsonl", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "w") as log:
            log.write(json.dumps(sample, sort_keys=True) + "\n")
            log.flush()
            os.fsync(log.fileno())
        report = assess(samples, a.hours)
        temporary = a.output / "report.tmp"
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(a.output / "report.json")
        print(json.dumps({k: report[k] for k in ("status", "samples", "elapsed_seconds")}), flush=True)
        if (time.monotonic() - start >= a.hours * 3600
                and (report["elapsed_seconds"] >= a.hours * 3600 or time.monotonic() - start >= a.hours * 3600 + 180)):
            return 0 if report["status"] == "passed" else 1
        time.sleep(max(0, a.interval - (time.monotonic() - cycle)))


if __name__ == "__main__":
    raise SystemExit(main())
