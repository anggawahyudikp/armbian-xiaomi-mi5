# Mi 5 Wi-Fi board data

The build requires the Mi 5-specific QCA6174 board data in both the early
initramfs and the installed rootfs. The previous generic `board.bin` allowed
association but produced very weak reported reception and unreliable discovery
on the audited phone. Supplying the original Mi 5 board data substantially
improved reception in a live driver test. Cold-boot and long-run validation of
the rebuilt image remain separate release requirements.

The [Linux Wireless calibration documentation](https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath10k/calibration.html)
explains that board data configures RF components, antenna capabilities and
gain tables. An unrelated QCA6174 template is insufficient evidence of correct
support for this phone. No transmit-power or regulatory limit is increased by
project configuration.

## Prepare the local build input

Obtain `image/bdwlan30.bin` from your backed-up Mi 5 **modem** partition. Do not
substitute a `persist` dump or another phone's firmware. Reading an existing
backup does not require flashing or mounting the phone. With `mtools` installed:

```sh
python3 scripts/prepare-wifi-board.py \
  --modem-image /path/to/mi5-modem.img \
  --output firmware/gemini/ath10k/QCA6174/hw3.0/board-pci-0000:01:00.0.bin
```

If the file was already extracted from the original firmware, use
`--source /path/to/bdwlan30.bin` instead of `--modem-image`.

```sh
python3 scripts/prepare-wifi-board.py --check
```

The validated input is 8,124 bytes with SHA-256
`31f673fa85adceda5ed480f2a1eaf2686e86c1ca9bbff49c35dc9a34e5a61430`.
The tool also checks its internal checksum. A missing or different input stops
the build; it does not silently fall back to the old generic board data.
Firmware inputs remain ignored by Git. Build provenance records the input
hash, and boot/rootfs/archive validation checks the installed copy.

The file is installed as
`usr/lib/firmware/ath10k/QCA6174/hw3.0/board-pci-0000:01:00.0.bin`.
Linux's QCA6174 API-1 fallback supports this device-specific filename. The
running driver's expected `board_file` CRC is `308ae9a4`; the previous generic
file reported `ed5f849a`. Both files have valid internal checksums, so a checksum
alone does not establish the right board identity.

Changing only the rootfs is insufficient: the built-in driver can load board
data before `switch_root`. Rebuild and validate the boot image as well. Keep the
previous boot backup and USB management available during hardware tests.

## Network identity

The board template's permanent MAC is not the phone's original unique address.
Generic images default to NetworkManager's `wifi.cloned-mac-address=stable`;
the first activation generates a local stable address using installation and
profile identity. A user's explicitly configured MAC still takes precedence.
The builder's NetworkManager `secret_key` is removed along with machine-id and
SSH keys. The image does not include a MAC copied from the audited phone.

Default selection follows the pinned
[NetworkManager 1.42 configuration rules](https://networkmanager.dev/docs/api/1.42.4/NetworkManager.conf.html).
