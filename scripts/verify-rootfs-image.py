#!/usr/bin/env python3
"""Check Android sparse roundtrip without mounting the filesystem."""
import argparse,json,pathlib,subprocess,tempfile
from artifact_identity import file_sha256
from wifi_board import TARGET as WIFI_BOARD_TARGET, validate as validate_wifi_board
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=pathlib.Path);a=p.parse_args();out=a.output.resolve()
images=json.loads((out/'rootfs-image-validation.json').read_text());assert images['passed']
assert file_sha256(out/'rootfs.img')==images['images']['rootfs.img']['sha256']
with tempfile.TemporaryDirectory(prefix='sparse-check-',dir=out) as directory:
 raw=pathlib.Path(directory)/'rootfs.ext4'
 subprocess.run(['simg2img',str(out/'rootfs.img'),str(raw)],check=True)
 digest=file_sha256(raw);assert digest==images['images']['rootfs.ext4']['sha256']
 priority=subprocess.check_output(['debugfs','-R','cat /etc/NetworkManager/conf.d/20-gemini-priority.conf',str(raw)],stderr=subprocess.DEVNULL)
 assert priority==(out/'rootfs/etc/NetworkManager/conf.d/20-gemini-priority.conf').read_bytes()
 watchdog=subprocess.check_output(['debugfs','-R','stat /etc/systemd/system/mi5-network-watchdog.service',str(raw)],stderr=subprocess.DEVNULL,text=True)
 assert 'symlink' in watchdog and '/dev/null' in watchdog
 board=subprocess.check_output(['debugfs','-R','cat /'+WIFI_BOARD_TARGET,str(raw)],stderr=subprocess.DEVNULL)
 validate_wifi_board(board)
 for dropin in ('serial-getty@.service.d/override.conf', 'serial-getty@ttyGS0.service.d/override.conf'):
  content=subprocess.check_output(['debugfs','-R','cat /etc/systemd/system/'+dropin,str(raw)],stderr=subprocess.DEVNULL)
  assert b'--autologin' not in content, 'USB root autologin survived image generation'
 report={'passed':True,'kernel_release':images['kernel_release'],'raw_sha256':digest,'expanded_sparse_sha256':digest,'wifi_primary_policy_preserved':True,'legacy_radio_watchdog_masked':True}
(out/'sparse-roundtrip-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Sparse rootfs expands to the validated raw ext4 byte for byte.')
