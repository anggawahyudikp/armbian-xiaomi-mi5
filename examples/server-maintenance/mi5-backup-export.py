#!/usr/bin/env python3
"""Export private system configuration and prepared, consistent app exports."""
from pathlib import Path
import datetime,gzip,io,json,os,subprocess,sys,tarfile
if os.geteuid()!=0:raise SystemExit('Run as root')
capacity=int(Path('/sys/class/power_supply/qcom-battery/capacity').read_text())
if capacity<=5:raise SystemExit('Battery at or below maintenance floor')
paths=['etc','root/.ssh','opt/stacks','var/backups/mi5-apps']
manifest={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'System configuration, Compose definitions and prepared application exports; not full userdata or live Docker volumes','battery_percent':capacity,'kernel':os.uname().release,'paths':[p for p in paths if (Path('/')/p).exists()],'app_export_policy':'Applications must export databases consistently into /var/backups/mi5-apps before backup. Live database volumes are not copied.'}
with gzip.GzipFile(fileobj=sys.stdout.buffer,mode='wb',compresslevel=1) as compressed, tarfile.open(fileobj=compressed,mode='w|') as tar:
 data=json.dumps(manifest,indent=2).encode();item=tarfile.TarInfo('mi5-backup-manifest.json');item.size=len(data);item.mode=0o600;tar.addfile(item,io.BytesIO(data))
 for p in manifest['paths']:tar.add('/'+p,arcname=p,recursive=True)
