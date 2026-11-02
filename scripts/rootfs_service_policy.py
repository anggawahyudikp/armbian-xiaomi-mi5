"""Remove the exact service-start blocker used while building the rootfs."""
from pathlib import Path
import argparse


def is_build_stub(path):
    path = Path(path)
    return (not path.is_symlink() and path.is_file()
            and path.read_bytes().strip() == b"#!/bin/sh\nexit 101")


def cleanup(root):
    policy = Path(root) / "usr/sbin/policy-rc.d"
    if is_build_stub(policy):
        policy.unlink()
        return True
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print("Removed build-only service policy:", cleanup(args.root))
