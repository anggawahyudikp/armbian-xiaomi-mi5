#!/usr/bin/env python3
"""Exercise kernel routes in a private netns; no Wi-Fi/USB hardware is emulated."""
import argparse
import configparser
import json
import os
import pathlib
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("policy", type=pathlib.Path)
parser.add_argument("--parent-netns", required=True)
parser.add_argument("--report", type=pathlib.Path, required=True)
args = parser.parse_args()
if os.readlink("/proc/self/ns/net") == args.parent_netns:
    raise SystemExit("Refusing to change routes outside a private netns")
policy = configparser.ConfigParser()
policy.read(args.policy)
cases = []


def ip(*arguments, required=True):
    result = subprocess.run(["ip", *arguments], capture_output=True, text=True)
    if required and result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result


ip("link", "set", "lo", "up")
for interface, v4, v6 in (("wifi-test", "192.0.2.2/24", "2001:db8:1::2/64"),
                          ("lan-test", "198.51.100.2/24", "2001:db8:2::2/64")):
    ip("link", "add", interface, "type", "dummy")
    ip("link", "set", interface, "up")
    ip("-4", "address", "add", v4, "dev", interface)
    ip("-6", "address", "add", v6, "dev", interface, "nodad")

for family, wifi_gateway, lan_gateway, destination in (
    ("ipv4", "192.0.2.1", "198.51.100.1", "203.0.113.10"),
    ("ipv6", "2001:db8:1::1", "2001:db8:2::1", "2001:db8:ffff::10"),
):
    switch = "-4" if family == "ipv4" else "-6"

    def add(interface, gateway, section):
        metric = policy.get(section, family + ".route-metric")
        ip(switch, "route", "add", "default", "via", gateway, "dev", interface, "metric", metric)

    def expect(name, interface):
        result = ip(switch, "route", "get", destination, required=False)
        if interface is None:
            assert result.returncode, f"{family}: unexpected route when both uplinks are absent"
        else:
            assert result.returncode == 0 and f"dev {interface} " in result.stdout, result.stdout + result.stderr
        cases.append({"family": family, "case": name, "passed": True})

    add("wifi-test", wifi_gateway, "connection-wifi")
    add("lan-test", lan_gateway, "connection-ethernet")
    expect("Both connected: prefer Wi-Fi", "wifi-test")
    # Model NetworkManager withdrawing the default route on disconnect.
    ip(switch, "route", "del", "default", "dev", "wifi-test")
    expect("Wi-Fi route withdrawn: use LAN", "lan-test")
    add("wifi-test", wifi_gateway, "connection-wifi")
    expect("Wi-Fi restored: prefer Wi-Fi again", "wifi-test")
    ip(switch, "route", "del", "default", "dev", "lan-test")
    expect("LAN absent: keep Wi-Fi", "wifi-test")
    ip(switch, "route", "del", "default", "dev", "wifi-test")
    expect("Both absent: no default route", None)

report = {"passed": True, "routing_simulation_only": True,
          "hardware_failover_verified": False, "cases": cases}
args.report.write_text(json.dumps(report, indent=2) + "\n")
print(f"Private network namespace: {len(cases)} IPv4/IPv6 routing cases passed")
