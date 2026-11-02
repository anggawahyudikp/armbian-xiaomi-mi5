# Xiaomi Mi 5 (gemini) debug UART

Public pad map from XDA: [Activating UART mode](https://xdaforums.com/t/activating-uart-mode.3834560/) (davidcie, 2018). It matches the ISL54062 µTQFN pinout and the Xiaomi schematic.

Third-party photos and datasheets are not redistributed in the public source tree. Consult the original sources and manufacturer datasheet for the pad references below.

## Which pads to solder

After hot-air removal of the RF/audio shield, find the unpopulated 1.8×1.4 mm 10-pin footprint (schematic `U711` / ISL54062). Production boards leave this analog switch unpopulated.

| Pad | Chip pin | Signal | USB-TTL adapter |
|-----|----------|--------|-----------------|
| **5** | NO2 | Phone **TX** (`MSM_UART_TX` / GPIO4) | Adapter **RX** |
| **8** | NO1 | Phone **RX** (`MSM_UART_RX` / GPIO5) | Adapter **TX** (optional if you only read logs) |
| **1** | GND | Ground | **GND** (required) |

Use the ISL54062 manufacturer datasheet for the micro-TQFN pinout; the 3 x 3 mm TDFN package has a different layout.

Boot log only: solder **5 + GND**.

## Settings

- **1.8 V** logic (not 3.3 V / 5 V; no level shifter can damage the SoC pin)
- **115200 8N1**, no flow control
- Kernel debug UART is `blsp2_uart2` @ `0x075b0000` (GPIO4/5), **not** the Bluetooth UART at `0x07570000`

## Do not solder these

The commonly shared **EDL** shorting points (9008 mode) are not UART pads.

## Reference sources

- [Original UART discussion](https://xdaforums.com/t/activating-uart-mode.3834560/)
- [Mi 5 teardown](https://www.myfixguide.com/manual/xiaomi-mi5-teardown/)
- Renesas ISL54062 datasheet, micro-TQFN pinout

Local reference copies are excluded from publication. No redistribution license
is asserted for third-party photos, datasheets or schematic images.
