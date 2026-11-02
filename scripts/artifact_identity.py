"""Content and metadata fingerprints used to reject stale build validation."""
import hashlib
import json
import os
import pathlib
import stat


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(root):
    """Do not follow symlinks, including absolute links in the target rootfs.

    Run inside the same root/user namespace as rootfs creation so ownership
    represents target IDs. Reject mounted pseudo-filesystems before hashing.
    """
    root = pathlib.Path(root).resolve()
    for name in ("dev", "proc", "sys", "run", "tmp", "var/tmp"):
        if os.path.ismount(root / name):
            raise ValueError(f"Unmount rootfs before validation: {name}")
    digest = hashlib.sha256()

    def visit(directory):
        for path in sorted(directory.iterdir()):
            info = path.lstat()
            record = [str(path.relative_to(root)), info.st_mode, info.st_uid, info.st_gid]
            if stat.S_ISLNK(info.st_mode):
                record.append(os.readlink(path))
            elif stat.S_ISREG(info.st_mode):
                record.append(file_sha256(path))
            elif stat.S_ISCHR(info.st_mode) or stat.S_ISBLK(info.st_mode):
                record.append(info.st_rdev)
            elif not stat.S_ISDIR(info.st_mode):
                raise ValueError(f"Unexpected rootfs file type: {path}")
            for name in sorted(os.listxattr(path, follow_symlinks=False)):
                record.append([name, os.getxattr(path, name, follow_symlinks=False).hex()])
            digest.update(json.dumps(record, ensure_ascii=True).encode() + b"\n")
            if stat.S_ISDIR(info.st_mode):
                visit(path)

    visit(root)
    return digest.hexdigest()


def validated_rootfs(root, report_path):
    report = json.loads(pathlib.Path(report_path).read_text())
    if report.get("passed") is not True:
        raise ValueError("Rootfs validation has not passed")
    if tree_sha256(root) != report.get("rootfs_sha256"):
        raise ValueError("Rootfs changed after validation; run verify-rootfs.py again")
    return report
