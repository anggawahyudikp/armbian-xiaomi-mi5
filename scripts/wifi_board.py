"""Identity of the Mi 5 board data verified against its original modem image."""
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / 'config/gemini-wifi-board.json').read_text())
TARGET = PROFILE['install_path']
SOURCE = ROOT / PROFILE['source_path']


def validate(data):
    if len(data) != PROFILE['bytes']:
        raise ValueError('Wrong Mi 5 Wi-Fi board data length')
    checksum = 0
    for (word,) in struct.iter_unpack('<H', data):
        checksum ^= word
    if checksum != 0xffff:
        raise ValueError('Invalid Mi 5 Wi-Fi board data checksum')
    digest = hashlib.sha256(data).hexdigest()
    if digest != PROFILE['sha256']:
        raise ValueError('Unverified Wi-Fi board data; the generic QCA6174 fallback is insufficient')
    if f'{zlib.crc32(data, 0xffffffff) ^ 0xffffffff:08x}' != PROFILE['linux_crc32']:
        raise ValueError('Wi-Fi board data CRC does not match the hardware observation')
    return digest
