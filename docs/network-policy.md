# Server network: Wi-Fi primary, LAN backup

The target workload is Docker and light applications. NetworkManager manages
connections and route selection. Wi-Fi defaults to metric 100 and Ethernet to
600 for both IPv4 and IPv6; lower metrics have priority. The policy does not
require fixed interface names such as `wlan0` or `eth0`.

The policy lives in
[`20-gemini-priority.conf`](../rootfs-overlay/etc/NetworkManager/conf.d/20-gemini-priority.conf),
installed through the rootfs overlay so builds and tests use the same source.
Defaults apply to profiles leaving `ipv4.route-metric` and `ipv6.route-metric`
at automatic `-1`. Explicit profile metrics retain their configured values.

| Connections with a default route | Selected uplink |
|---|---|
| Wi-Fi and LAN | Wi-Fi |
| LAN only after Wi-Fi disconnects | LAN |
| Wi-Fi regains a default route | Wi-Fi |
| Wi-Fi only | Wi-Fi |
| Neither | No uplink through either connection |

Selection happens separately for each IP family. If Wi-Fi supplies IPv4 only
and LAN supplies IPv6, IPv6 traffic can still use LAN. The backup interface can
remain active with its own address. A changed route/source address may require
applications to reconnect; session continuity is not guaranteed.

This policy handles connection and route withdrawal/recovery. Wi-Fi that stays
associated while losing Internet access does not automatically fail over based
on metrics alone. Active Internet probing has not been added. A shared router
or ISP can affect both Wi-Fi and LAN.

The old `mi5-network-watchdog.service` remains masked. It pinged the gateway and
cycled the Wi-Fi radio, which could unnecessarily disconnect Wi-Fi when ICMP
was blocked or a different uplink failed. NetworkManager handles normal saved
profile autoconnection. The optional bounded profile retry helper is described
in the [stability plan](stability-plan.md).

Offline checks:

- `verify-rootfs.py` asks the target ARM64 NetworkManager to print its merged
  configuration, checks IPv4/IPv6 metrics and verifies the watchdog mask. It
  does not start a target networking daemon on the build host.
- `bash tests/network/run.sh` uses a new network namespace and two dummy
  interfaces to exercise ten route selection, withdrawal and recovery cases.
  It does not change laptop routing or emulate Wi-Fi/USB drivers.
- Release ZIP validation reads the policy and watchdog mask from the packaged
  rootfs tarball.

On hardware, inspect `ip -4 route show default` and `ip -6 route show default`,
then test Wi-Fi loss/recovery with a real LAN adapter connected. Monitor SSH and
Docker through both paths. Provision Wi-Fi credentials locally; the image
contains no builder SSID/password.

LAN still needs USB host and power support demonstrated on the phone. Bring-up
starts with Wi-Fi/SSH/Docker, followed by physical backup LAN testing.

Reference: [NetworkManager 1.42.4 configuration](https://networkmanager.dev/docs/api/1.42.4/NetworkManager.conf.html).
