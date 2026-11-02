#!/bin/sh
# Legacy entry point; one service owns the UDC and serial handoff.
case "${1:-start}" in
 start) exec systemctl start mi5-usb-gadget.service mi5-usb-dhcp.service;;
 stop) exec systemctl stop mi5-usb-dhcp.service mi5-usb-gadget.service;;
 restart) exec systemctl restart mi5-usb-gadget.service mi5-usb-dhcp.service;;
 *) echo 'Usage: usb-gadget-rndis.sh start|stop|restart' >&2; exit 2;;
esac
