#!/usr/bin/env bash
# ==============================================================================
# mi5-power-guard : Smart Battery Health & UPS Daemon for Xiaomi Mi 5 (gemini)
# Protects battery health during 24/7 plugged server use and acts as UPS.
# ==============================================================================

LOG_TAG="mi5-power-guard"
CONF_FILE="/etc/default/mi5-charge-limit"

log() {
    logger -t "$LOG_TAG" "$1"
    echo "[$LOG_TAG] $1"
}

get_charge_limit() {
    if [ -f "$CONF_FILE" ]; then
        cat "$CONF_FILE"
    else
        echo 70
    fi
}

find_batt_dir() {
    for d in /sys/class/power_supply/*battery* /sys/class/power_supply/*batt* /sys/class/power_supply/*fg*; do
        [ -d "$d" ] && { echo "$d"; return; }
    done
    echo "/sys/class/power_supply/battery"
}

find_usb_dir() {
    for d in /sys/class/power_supply/*usb* /sys/class/power_supply/*smb* /sys/class/power_supply/*charger*; do
        [ -d "$d" ] && { echo "$d"; return; }
    done
    echo "/sys/class/power_supply/usb"
}

set_charging() {
    local enable=$1 # 1 or 0
    local bdir udir
    bdir=$(find_batt_dir)
    udir=$(find_usb_dir)

    for node in \
        "$bdir/charging_enabled" \
        "$bdir/battery_charging_enabled" \
        "$udir/charging_enabled" \
        "$udir/online" \
        /sys/class/power_supply/qcom-smbchg/charging_enabled \
        /sys/class/power_supply/battery/charging_enabled; do
        if [ -w "$node" ]; then
            echo "$enable" > "$node" 2>/dev/null || true
        fi
    done
}

log "Starting Xiaomi Mi 5 Power Guard & UPS Daemon..."

LAST_AC_STATUS=""

while true; do
    LIMIT=$(get_charge_limit)
    BATT_DIR=$(find_batt_dir)
    USB_DIR=$(find_usb_dir)

    CAP=$(cat "$BATT_DIR/capacity" 2>/dev/null || cat /sys/class/power_supply/battery/capacity 2>/dev/null || echo 100)
    STATUS=$(cat "$BATT_DIR/status" 2>/dev/null || echo "Unknown")
    ONLINE=$(cat "$USB_DIR/online" 2>/dev/null || cat /sys/class/power_supply/usb/online 2>/dev/null || echo 1)

    # 1. AC Power Loss / Restore Monitor
    if [ "$ONLINE" -eq 0 ] && [ "$LAST_AC_STATUS" != "offline" ]; then
        log "[ALERT] AC Power disconnected! Server is running on internal UPS battery (Level: ${CAP}%)."
        LAST_AC_STATUS="offline"
    elif [ "$ONLINE" -eq 1 ] && [ "$LAST_AC_STATUS" == "offline" ]; then
        log "[INFO] AC Power restored! Running on mains."
        LAST_AC_STATUS="online"
        set_charging 1
    fi

    # 2. Emergency Shutdown during extended power cut
    if [ "$ONLINE" -eq 0 ] && [ "$CAP" -le 8 ]; then
        log "[CRITICAL] Battery level critically low (${CAP}%). Initiating graceful shutdown to prevent data corruption..."
        shutdown -h now "UPS Battery Depleted"
        exit 0
    fi

    # 3. 24/7 Battery Health Protection (Prevent Swelling)
    if [ "$ONLINE" -eq 1 ]; then
        if [ "$LIMIT" -lt 100 ]; then
            if [ "$CAP" -ge "$LIMIT" ]; then
                set_charging 0
            elif [ "$CAP" -le $(( LIMIT - 15 )) ]; then
                set_charging 1
            fi
        else
            set_charging 1
        fi
    fi

    sleep 15
done
