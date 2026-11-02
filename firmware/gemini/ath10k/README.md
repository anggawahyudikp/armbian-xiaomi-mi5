# ath10k firmware (QCA6174)

Board/firmware blobs for PCIe QCA6174 belong here. They are gitignored. Copy them from the device `lib/firmware/ath10k/` when building a rootfs.

The current build requires verified Mi 5 board data from the original modem
firmware. Follow [Wi-Fi board data preparation](../../../docs/wifi-board-data.md);
the generic `board.bin` is not an adequate substitute.
