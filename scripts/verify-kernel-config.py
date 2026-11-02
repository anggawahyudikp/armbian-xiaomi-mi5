#!/usr/bin/env python3
"""Reject a kernel which cannot support the Gemini rootfs and advertised swap."""
import pathlib
import sys

config = dict(line.split("=", 1) for line in pathlib.Path(sys.argv[1]).read_text().splitlines()
              if line.startswith("CONFIG_") and "=" in line)
required = {
    "ARCH_QCOM": "y", "RELOCATABLE": "y", "PSTORE": "y", "PSTORE_RAM": "y",
    "PSTORE_CONSOLE": "y", "PSTORE_PMSG": "y",
    "ARM64_VA_BITS": "48", "BLK_DEV_INITRD": "y", "RD_GZIP": "y",
    "DEVTMPFS": "y", "TMPFS": "y", "SCSI": "y", "BLK_DEV_SD": "y",
    "SCSI_UFSHCD": "y", "SCSI_UFS_QCOM": "y", "EXT4_FS": "y",
    "EFI_PARTITION": "y", "USB_G_SERIAL": "y", "U_SERIAL_CONSOLE": "y",
    "USB_GADGET_VBUS_DRAW": "500", "CHARGER_QCOM_SMBCHG": "y", "BATTERY_QCOM_FG": "y",
    "DRM_MSM": "m", "DRM_PANEL_JDI_R63452": "m",
    "THERMAL": "y", "CPU_THERMAL": "y", "THERMAL_GOV_STEP_WISE": "y",
    "ATH10K_PCI": "y", "ZRAM": "m", "ZRAM_BACKEND_ZSTD": "y",
    "ZRAM_DEF_COMP": '"zstd"', "USB_RTL8152": "y",
    "USB_NET_AX88179_178A": "y", "OVERLAY_FS": "y", "MEMCG": "y",
    "NET_NS": "y", "VETH": "y", "BRIDGE": "y",
}
# Enforce the container capabilities already requested by gemini.fragment.
# Moby's contrib/check-config.sh documents the core namespace/cgroup/netfilter
# requirements. Also retain this port's seccomp, resource limits, nftables and
# ext4/overlay choices; checking only MEMCG/NET_NS/VETH/BRIDGE is insufficient.
# These are configuration checks, not proof that Docker runs on the phone.
required.update(dict.fromkeys("""
    NAMESPACES NET_NS PID_NS IPC_NS UTS_NS USER_NS
    CGROUPS CGROUP_CPUACCT CGROUP_DEVICE CGROUP_FREEZER CGROUP_SCHED CPUSETS MEMCG
    CGROUP_PIDS CGROUP_BPF FAIR_GROUP_SCHED CFS_BANDWIDTH BLK_CGROUP BLK_DEV_THROTTLING
    SECCOMP SECCOMP_FILTER KEYS POSIX_MQUEUE
    VETH BRIDGE BRIDGE_NETFILTER
    IP_NF_FILTER IP_NF_MANGLE IP_NF_TARGET_MASQUERADE IP_NF_RAW IP_NF_NAT
    IP6_NF_FILTER IP6_NF_MANGLE IP6_NF_TARGET_MASQUERADE IP6_NF_RAW IP6_NF_NAT
    NETFILTER_XT_MATCH_ADDRTYPE NETFILTER_XT_MATCH_CONNTRACK
    NETFILTER_XT_MATCH_IPVS NETFILTER_XT_MARK NF_CONNTRACK NF_NAT
    NF_TABLES NFT_CT NFT_MASQ NFT_NAT NFT_COMPAT
    EXT4_FS_POSIX_ACL EXT4_FS_SECURITY OVERLAY_FS
""".split(), "y"))
errors = [f"CONFIG_{key}: expected {value}, got {config.get('CONFIG_' + key, 'unset')}"
          for key, value in required.items() if config.get("CONFIG_" + key) != value]
# The modular PMIC RTC can otherwise overwrite the restored boot clock.
if config.get("CONFIG_RTC_HCTOSYS") not in (None, "n"):
    errors.append("CONFIG_RTC_HCTOSYS: must be disabled to prevent late RTC clock regression")
if errors:
    raise SystemExit("Kernel configuration failed:\n" + "\n".join(errors))
print(f"Kernel configuration: {len(required)} required settings verified; RTC boot-clock policy verified")
