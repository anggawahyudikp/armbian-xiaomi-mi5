#!/usr/bin/env python3
"""Pull a verified private Mi 5 backup; retain fourteen successful snapshots."""
from pathlib import Path
import datetime,fcntl,gzip,hashlib,json,os,subprocess,tarfile
os.umask(0o077)
base=Path.home()/'mi5-backups';base.mkdir(mode=0o700,exist_ok=True);base.chmod(0o700)
lock=(base/'.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');target=base/f'mi5-{stamp}.tar.gz';partial=target.with_suffix(target.suffix+'.partial')
try:
 with partial.open('xb') as out:
  os.fchmod(out.fileno(),0o600)
  subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','mi5-armbian','/usr/local/sbin/mi5-backup-export'],stdout=out,check=True,timeout=300)
  out.flush();os.fsync(out.fileno())
 with gzip.open(partial,'rb') as stream:
  while stream.read(1024*1024):pass
 with tarfile.open(partial,'r:gz') as tar:
  names=tar.getnames();assert 'mi5-backup-manifest.json' in names and 'etc/ssh/sshd_config' in names
  assert all(not n.startswith('/') and '..' not in Path(n).parts for n in names)
  manifest=json.load(tar.extractfile('mi5-backup-manifest.json'))
 with partial.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
 assert not target.exists();partial.rename(target)
 sums=target.with_suffix(target.suffix+'.sha256');sums.write_text(digest+'  '+target.name+'\n');sums.chmod(0o600)
 report={'verified':True,'archive':target.name,'bytes':target.stat().st_size,'sha256':digest,'entries':len(names),'scope':manifest['scope'],'created_utc':manifest['created_utc']}
 p=base/'latest.json.tmp';p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o600);p.replace(base/'latest.json')
 for old in sorted(base.glob('mi5-*.tar.gz'))[:-14]:
  old.unlink();old.with_suffix(old.suffix+'.sha256').unlink(missing_ok=True)
 print('Mi 5 backup verified: '+target.name)
finally:
 partial.unlink(missing_ok=True)
