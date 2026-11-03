#!/usr/bin/env bash
# LAN/USB maintenance and Docker publishing policy; preserve Docker's own chains.
set -euo pipefail
TRUSTED_IPV4='10.0.0.0/8 172.16.0.0/12 192.168.0.0/16'
TRUSTED_IPV6='fc00::/7 fe80::/10'
HOST_TCP_PORTS='22'
[[ ! -f /etc/default/mi5-server-firewall ]] || source /etc/default/mi5-server-firewall
for tool in iptables ip6tables; do
    "$tool" -w -N MI5-HOST 2>/dev/null || "$tool" -w -S MI5-HOST >/dev/null
    "$tool" -w -F MI5-HOST
    "$tool" -w -A MI5-HOST -i lo -j ACCEPT
    "$tool" -w -A MI5-HOST -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    "$tool" -w -A MI5-HOST -m conntrack --ctstate INVALID -j DROP
    if [[ "$tool" == iptables ]]; then
        ranges=$TRUSTED_IPV4
        "$tool" -w -A MI5-HOST -p icmp -j ACCEPT
        "$tool" -w -A MI5-HOST -i wlan0 -p udp --sport 67 --dport 68 -j ACCEPT
        "$tool" -w -A MI5-HOST -i usb0 -p udp --dport 67 -j ACCEPT
    else
        ranges=$TRUSTED_IPV6
        "$tool" -w -A MI5-HOST -p ipv6-icmp -j ACCEPT
        "$tool" -w -A MI5-HOST -i wlan0 -p udp --sport 547 --dport 546 -j ACCEPT
    fi
    for network in $ranges; do
        for port in $HOST_TCP_PORTS; do
            "$tool" -w -A MI5-HOST -s "$network" -p tcp --dport "$port" -j ACCEPT
        done
    done
    "$tool" -w -A MI5-HOST -j DROP
    "$tool" -w -C INPUT -j MI5-HOST 2>/dev/null || "$tool" -w -I INPUT 1 -j MI5-HOST
    "$tool" -w -N DOCKER-USER 2>/dev/null || "$tool" -w -S DOCKER-USER >/dev/null
    "$tool" -w -N MI5-DOCKER 2>/dev/null || "$tool" -w -S MI5-DOCKER >/dev/null
    "$tool" -w -F MI5-DOCKER
    "$tool" -w -A MI5-DOCKER -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
    "$tool" -w -A MI5-DOCKER -m conntrack --ctstate INVALID -j DROP
    "$tool" -w -A MI5-DOCKER -i docker0 -j RETURN
    "$tool" -w -A MI5-DOCKER -i br+ -j RETURN
    "$tool" -w -A MI5-DOCKER -i lo -j RETURN
    for network in $ranges; do "$tool" -w -A MI5-DOCKER -s "$network" -j RETURN; done
    "$tool" -w -A MI5-DOCKER -j DROP
    "$tool" -w -C DOCKER-USER -j MI5-DOCKER 2>/dev/null || "$tool" -w -I DOCKER-USER 1 -j MI5-DOCKER
    "$tool" -w -C FORWARD -j DOCKER-USER 2>/dev/null || "$tool" -w -I FORWARD 1 -j DOCKER-USER
 done
