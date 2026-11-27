# ESP32-S3 bring-up test

Date: 2026-11-21

## Setup

- Board stated by user: ESP32-S3-DevKitC-1 N16R8.
- Port: COM4, USB-Enhanced-SERIAL CH343; serial console at 115200 baud.
- ESP-IDF: v6.1.1, as reported by the device boot log.
- The generated `sdkconfig` selected `esp32s3` and 16 MB flash.
- `esptool flash-id` identified an ESP32-S3 revision v0.2, embedded PSRAM 8 MB and 16 MB flash. This identification did not test PSRAM.

## Procedure and result

1. The first ESP-IDF MCP build call timed out; build artifacts appeared afterward, but that alone was not treated as proof of success.
2. A second incremental ESP-IDF MCP build returned `Successfully built project`.
3. ESP-IDF MCP flash on COM4 returned `Successfully flashed project to port COM4`.
4. A serial reader captured about 8 seconds of boot and application output. Selected lines:

```text
I (24) boot: ESP-IDF v6.1.1 2nd stage bootloader
I (32) boot.esp32s3: SPI Flash Size : 16MB
I (143) app_init: Project name:     fyp_radar_template
I (253) main_task: Calling app_main()
I (253) fyp: FYP radar template started; radar input is not implemented
I (253) fyp: heartbeat=1 presence=UNAVAILABLE
I (2253) fyp: heartbeat=2 presence=UNAVAILABLE
I (4253) fyp: heartbeat=3 presence=UNAVAILABLE
I (6253) fyp: heartbeat=4 presence=UNAVAILABLE
I (8253) fyp: heartbeat=5 presence=UNAVAILABLE
```

## Scope

The log demonstrates this firmware started and emitted repeated heartbeats during the short capture. It does not establish long-term stability, radar reception, occupancy accuracy, lamp control, PSRAM functionality or compliance with FYP acceptance requirements. `UNAVAILABLE` is the intentional placeholder, not an inferred empty room.
