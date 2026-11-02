#!/usr/bin/env python3
"""Record verified release identity and keep device evidence separately scoped."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from artifact_identity import file_sha256
from boot_layout import PROFILE
from project_metadata import PROJECT, artifact_names
from wifi_board import SOURCE as WIFI_BOARD_SOURCE, validate as validate_wifi_board
from kernel_source_identity import source_patch

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('output',type=Path)
p.add_argument('--kernel-output',type=Path,required=True)
a=p.parse_args();out=a.output.resolve();kernel=a.kernel_output.resolve()
root=Path(__file__).resolve().parents[1]
built_source=kernel/'source'
kernel_source=(built_source if built_source.is_dir() else Path(os.environ.get('KERNEL_SRC',root/'linux'))).resolve()
if os.environ.get('KERNEL_SRC') and Path(os.environ['KERNEL_SRC']).resolve()!=kernel_source:
 raise SystemExit('KERNEL_SRC differs from the selected kernel output source')
reports={name:json.loads((out/path).read_text()) for name,path in {
 'production':'boot-validation.json','diagnostic':'boot-diagnostic-validation.json',
 'usb_debug':'usb-debug-verification.json','rootfs':'rootfs-validation.json',
 'images':'rootfs-image-validation.json','roundtrip':'sparse-roundtrip-validation.json',
 'release':'release-validation.json'}.items()}
assert all(r['passed'] for r in reports.values())
krel=(kernel/'include/config/kernel.release').read_text().strip()
assert all(reports[n]['kernel_release']==krel for n in ('production','diagnostic','usb_debug','rootfs','images','roundtrip'))
shutil.copyfile(kernel/'.config',out/'kernel.config')
names=artifact_names()
artifacts=('boot.img','boot-diagnostic.img','boot-diagnostic-usb-debug.img','rootfs.ext4','rootfs.img',names['fastboot'],names['twrp'])
outputs={n:file_sha256(out/n) for n in (*artifacts,'kernel.config','Image.gz','msm8996-xiaomi-gemini.dtb')}
for n in ('rootfs.ext4','rootfs.img'):assert outputs[n]==reports['images']['images'][n]['sha256']
for n,key in (('boot.img','production'),('boot-diagnostic.img','diagnostic'),('boot-diagnostic-usb-debug.img','usb_debug')):
 assert outputs[n]==reports[key]['sha256']
inputs={}
for directory in ('scripts','config','initramfs','overlays','armbian','rootfs-overlay','tests'):
 for path in sorted((root/directory).rglob('*')):
  if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts:
   inputs[str(path.relative_to(root))]=file_sha256(path)
inputs[str(WIFI_BOARD_SOURCE.relative_to(root))] = validate_wifi_board(WIFI_BOARD_SOURCE.read_bytes())
patch=source_patch(kernel_source)
(out/'kernel-source.patch').write_bytes(patch)
report={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'project':PROJECT,'offline_validation_passed':True,'generic_rootfs_hardware_boot_verified':False,
 'kernel_release':krel,'bootloader_profile':PROFILE,
 'kernel_source_commit':subprocess.check_output(['git','-C',str(kernel_source),'rev-parse','HEAD'],text=True).strip(),
 'kernel_source_patch_sha256':hashlib.sha256(patch).hexdigest(),
 'armbian_framework_commit':(root/'armbian/framework-revision').read_text().strip(),
 'inputs':inputs,'outputs':outputs,'rootfs_sha256':reports['rootfs']['rootfs_sha256'],
 'runtime_evidence':[]}
for name in ('native-runtime-validation.json','server-console-runtime.json'):
 if (out/name).is_file():report['runtime_evidence'].append({'path':name,'sha256':file_sha256(out/name)})
(out/'SHA256SUMS').write_text(''.join(outputs[n]+'  '+n+'\n' for n in artifacts))
(out/'build-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
print('Recorded verified project release, seven artifacts and scoped runtime evidence.')
