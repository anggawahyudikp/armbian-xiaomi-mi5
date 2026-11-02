#!/usr/bin/env bash
# ==============================================================================
# mi5-network-watchdog : Self-Healing Network Daemon for Xiaomi Mi 5 Armbian
# Automatically detects Wi-Fi/network drops and re-establishes connectivity.
# Does NOT drop host USB or wired links when offline.
# ==============================================================================

LOG_TAG="mi5-net-watchdog"
FAIL_COUNT=0
MAX_FAILURES=4

log() {
    logger -t "$LOG_TAG" "$1"
    echo "[$LOG_TAG] $1"
}

get_gateway() {
    ip route | awk '/default/ {print $3; exit}'
}

has_active_carrier() {
    # Check if eth0, usb0, or wlan0 is connected
    for dev in eth0 usb0 rndis0 wlan0 wlp1s0; do
        if [ -f "/sys/class/net/$dev/carrier" ] && [ "$(cat /sys/class/net/$dev/carrier 2>/dev/null)" = "1" ]; then
            return 0
        fi
    done
    return 1
}

log "Starting Network Self-Healing Watchdog..."

# Wait 60s on boot before starting health checks
sleep 60

while true; do
    GW=$(get_gateway)

    if [ -n "$GW" ]; then
        # Send 3 pings, succeed if at least 1 packet returns
        if ping -c 3 -W 2 -q "$GW" >/dev/null 2>&1; then
            FAIL_COUNT=0
        else
            FAIL_COUNT=$(( FAIL_COUNT + 1 ))
            log "[WARN] Default gateway $GW unreachable (Failure $FAIL_COUNT of $MAX_FAILURES)"
        fi
    else
        # If no default gateway, but an interface is physically connected (like USB gadget or LAN), do not panic
        FAIL_COUNT=0
    fi

    if [ "$FAIL_COUNT" -ge "$MAX_FAILURES" ]; then
        log "[ALERT] Gateway unreachable. Triggering Wi-Fi radio cycle to self-heal..."
        if command -v nmcli >/dev/null; then
            # Cycle only Wi-Fi radio so wired Ethernet/USB gadget remains intact
            nmcli radio wifi off 2>/dev/null || true
            sleep 2
            nmcli radio wifi on 2>/dev/null || true
        else
            for iface in wlan0 wlp1s0; do
                if [ -d "/sys/class/net/$iface" ]; then
                    ip link set "$iface" down 2>/dev/null || true
                    sleep 2
                    ip link set "$iface" up 2>/dev/null || true
                fi
            done
        fi
        FAIL_COUNT=0
        sleep 45
    fi

    sleep 45
done
