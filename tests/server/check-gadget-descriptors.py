#!/usr/bin/python3
"""Read-only validation on a running Mi 5; no host enumeration is implied."""
from pathlib import Path
import json
root=Path('/sys/kernel/config/usb_gadget/mi5')
def value(name):return (root/name).read_text().strip().rstrip('\0')
assert value('UDC')
assert value('idVendor')=='0x1d6b' and value('idProduct')=='0x0104'
assert value('bDeviceClass')=='0xef'
assert value('configs/c.1/MaxPower')=='500'
assert value('functions/acm.usb0/port_num')=='0'
assert (root/'configs/c.1/acm.usb0').is_symlink()
status=json.loads(Path('/run/mi5-usb/status.json').read_text())
mode=status['mode']
revision={'rndis':0x0102,'ncm':0x0103}[mode]
assert int(value('bcdDevice'),0)==revision
assert int(status['device_revision'],0)==revision
assert value('functions/'+mode+'.usb0/ifname')=='usb0'
assert (root/('configs/c.1/'+mode+'.usb0')).is_symlink()
if mode=='rndis':
 assert value('os_desc/use')=='1'
 assert value('os_desc/qw_sign')=='MSFT100'
 assert value('functions/rndis.usb0/os_desc/interface.rndis/compatible_id')=='RNDIS'
 assert value('functions/rndis.usb0/os_desc/interface.rndis/sub_compatible_id')=='5162001'
 assert (root/'os_desc/c.1').resolve()==root/'configs/c.1'
dhcp=Path('/run/mi5-usb/dnsmasq.conf').read_text()
assert 'interface=usb0\n' in dhcp
assert 'port=0\n' in dhcp
assert 'dhcp-option=option:router\n' in dhcp
assert 'dhcp-option=option:dns-server\n' in dhcp
print('PASS:',mode,'ACM, descriptors, 500 mA declaration and local-only DHCP configuration')
