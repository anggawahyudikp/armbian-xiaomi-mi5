"""Stock Gemini LK layout, verified from the installed aboot binary.

LK overwrites Android header addresses. A small ARM64 branch wrapper bridges
its fixed 512 KiB load offset to an aligned mainline Image at DDR + 2 MiB.
"""
import json
import pathlib
import struct
import zlib

profile_path = pathlib.Path(__file__).with_name("gemini-lk.json")
if not profile_path.exists():
    profile_path = pathlib.Path(__file__).resolve().parents[1] / "config/gemini-lk.json"
PROFILE = json.loads(profile_path.read_text())
KERNEL_ADDRESS = PROFILE["kernel_address"]
RAMDISK_ADDRESS = PROFILE["ramdisk_address"]
DTB_ADDRESS = PROFILE["dtb_address"]
REAL_KERNEL_ADDRESS = PROFILE["real_kernel_address"]
RAMDISK_LIMIT = 0x85800000  # First fixed firmware reservation in Gemini DTB.
PAGE_SIZE = PROFILE["page_size"]
SHIM_SIZE = REAL_KERNEL_ADDRESS - KERNEL_ADDRESS
SHIM_MARKER = b"MI5-LK64-SHIM-v1\0"
ARM64_MAGIC = 0x644D5241
NOP = 0xD503201F
BRANCH = 0x14000000 | ((SHIM_SIZE - 4) // 4)


def arm64_header(image):
    if len(image) < 64:
        raise ValueError("Truncated ARM64 Image header")
    fields = struct.unpack_from("<2I6Q2I", image)
    if fields[8] != ARM64_MAGIC or fields[4] & 1:
        raise ValueError("Expected little-endian ARM64 Image")
    return fields


def wrap_kernel(image):
    fields = arm64_header(image)
    if fields[2] != 0 or not fields[3]:
        raise ValueError("Expected a mainline Image with text_offset=0 and known image_size")
    span = max(len(image), fields[3])
    if REAL_KERNEL_ADDRESS + span > DTB_ADDRESS:
        raise ValueError(f"Kernel needs {span} bytes; stock LK permits only "
                         f"{DTB_ADDRESS - REAL_KERNEL_ADDRESS} bytes before DTB")
    shim = bytearray(SHIM_SIZE)
    struct.pack_into("<2I6Q2I", shim, 0, NOP, BRANCH,
                     KERNEL_ADDRESS - PROFILE["ddr_base"], SHIM_SIZE + span,
                     fields[4], 0, 0, 0, ARM64_MAGIC, 0)
    shim[64:64 + len(SHIM_MARKER)] = SHIM_MARKER
    return bytes(shim) + image


def unwrap_kernel(payload):
    outer = arm64_header(payload)
    if outer[:2] != (NOP, BRANCH) or payload[64:64 + len(SHIM_MARKER)] != SHIM_MARKER:
        raise ValueError("Missing Gemini LK alignment wrapper; rebuild the boot image")
    if outer[2] != KERNEL_ADDRESS - PROFILE["ddr_base"]:
        raise ValueError("Wrapper load offset does not match installed stock LK")
    image = payload[SHIM_SIZE:]
    inner = arm64_header(image)
    span = max(len(image), inner[3])
    if inner[2] != 0 or not inner[3] or REAL_KERNEL_ADDRESS % (2 * 1024 * 1024):
        raise ValueError("Inner mainline Image is not aligned according to its ARM64 header")
    if outer[3] != SHIM_SIZE + span or REAL_KERNEL_ADDRESS + span > DTB_ADDRESS:
        raise ValueError("Kernel overlaps stock LK's forced DTB address")
    return image, {"wrapper_bytes": SHIM_SIZE, "kernel_address": KERNEL_ADDRESS,
                   "real_kernel_address": REAL_KERNEL_ADDRESS,
                   "real_kernel_span": span, "kernel_memory_end": REAL_KERNEL_ADDRESS + span,
                   "dtb_address": DTB_ADDRESS, "ramdisk_address": RAMDISK_ADDRESS}


def parse_boot_image(blob):
    if not 48 <= len(blob) <= 64 * 1024 * 1024:
        raise ValueError("Boot image is truncated or larger than the Mi 5 boot partition")
    h = struct.unpack_from("<8s9I", blob)
    if (h[0], h[2], h[4], h[7], h[8], h[9]) != (
        b"ANDROID!", KERNEL_ADDRESS, RAMDISK_ADDRESS, DTB_ADDRESS, PAGE_SIZE, 0
    ):
        raise ValueError("Boot header does not match the verified Gemini stock LK layout")
    kernel_size, ramdisk_size = h[1], h[3]
    if h[5] != 0:
        raise ValueError("Gemini images must not contain an unsupported second-stage payload")
    rd_offset = PAGE_SIZE + (kernel_size + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE
    if not kernel_size or not ramdisk_size or rd_offset + ramdisk_size > len(blob):
        raise ValueError("Truncated or empty boot payload")
    decoder = zlib.decompressobj(31)
    try:
        payload = decoder.decompress(blob[PAGE_SIZE:PAGE_SIZE + kernel_size], DTB_ADDRESS - KERNEL_ADDRESS + 1)
    except zlib.error as exc:
        raise ValueError("Invalid compressed kernel") from exc
    if len(payload) > DTB_ADDRESS - KERNEL_ADDRESS or not decoder.eof or decoder.unconsumed_tail:
        raise ValueError("Compressed kernel exceeds the stock LK memory window or is truncated")
    dtb = decoder.unused_data
    if len(dtb) < 8 or dtb[:4] != b"\xd0\x0d\xfe\xed" or struct.unpack_from(">I", dtb, 4)[0] != len(dtb):
        raise ValueError("Missing or malformed appended DTB")
    if DTB_ADDRESS + len(dtb) > RAMDISK_ADDRESS:
        raise ValueError("DTB overlaps stock LK ramdisk address")
    if RAMDISK_ADDRESS + ramdisk_size > RAMDISK_LIMIT:
        raise ValueError("Ramdisk overlaps fixed firmware reserved memory")
    image, layout = unwrap_kernel(payload)
    return image, dtb, blob[rd_offset:rd_offset + ramdisk_size], layout
