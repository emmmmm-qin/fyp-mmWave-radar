# ESP32-S3 radar telemetry bridge

The firmware listens to an **externally configured and started** TI radar. It never sends CLI commands, fabricates frames, or decides occupancy. If no supported packet arrives, the PC receives `unavailable`, not an empty-room reading.

## Connect and configure

1. Use a compatible xWRL6432 Motion and Presence Detection image/profile (see [supported wire format](docs/ti_radar_research.md)). Configure it separately to emit compressed points (`guiMonitor` point-cloud mode `2`). Confirm the **actual data baud** after sensor start; it need not equal the CLI baud.
2. With power off, connect the verified **3.3 V logic** radar data TX to ESP32-S3 **GPIO18** and connect grounds. Use level translation for other logic levels; never feed RS-232 or 5 V into an ESP GPIO. Leave radar RX, ESP TX, and flow-control lines disconnected. Power each board according to its own guide. Check the actual board schematic for pin conflicts.
3. Open an ESP-IDF terminal in this directory (build verified with v6.1.1). For a new configuration run `idf.py set-target esp32s3`, then `idf.py menuconfig` if needed and `idf.py build`. Under **FYP radar input**, defaults are UART1, RX GPIO18, **115200 8N1**, no flow control. Set baud to match the radar, e.g. 1250000 if that is its configured output. Allowed controllers are UART1/2 and RX pins GPIO4–18, a conservative subset excluding USB, straps and flash/PSRAM pins. This is not a guarantee that every allowed pin is free on your carrier. Defaults assume 16 MB flash; adapt for other modules. If reusing `sdkconfig`, ensure **USB Serial/JTAG Controller** is the primary console (not USB OTG CDC or UART).
4. On a board running the firmware, use a data cable on the **native USB** connector (GPIO19 D−, GPIO20 D+), not the CH343/USB-UART port used in the historical bring-up. Open its COM port in one reader at a time. USB line speed is independent of the radar baud. Ignore non-protocol boot/self-test lines. See [Espressif USB Serial/JTAG console](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/usb-serial-jtag-console.html).

## What the host receives

ASCII NDJSON, one object per line. `protocol="fyp-radar"`, `v=1`, `source="radar"`. Valid packets use the TI frame number as `seq` and ESP uptime in milliseconds as `t_ms`. `cloud` carries 1–100 `[x_m,y_m,radial_velocity_mps]` triples; `no_cloud` means a **valid** frame without the supported cloud. During startup/silence, `unavailable` uses `seq=0` and `points=[]`: immediately while waiting, then once a second, beginning two seconds after the last valid packet. Invalid input does not refresh liveness.

The receiver handles fragmented/concatenated packets and scans rejected candidates for the next sync. Maximum packet size is 8192 bytes including padding. Partial candidates expire after 250 ms without bytes or 2 s total. Larger optional radar outputs (e.g. heatmaps) may exceed this limit; disable them or validate and revise the cap. A separate, lower-priority stdout task takes the latest sample from a one-slot mailbox; under USB backpressure old samples may be skipped. This is a live display, not lossless recording. Host software should reject malformed/partial lines and expire stale displays even if USB disconnects. The boot self-test is diagnostic text only.

## Native verification (no device)

```
cmake -S tests -B build-host
cmake --build build-host
ctest --test-dir build-host --output-on-failure
```

For multi-config generators specify `--config Debug` on build and `-C Debug` on CTest. `ti_mpd_packet_test --emit-fixture` prints one synthetic decoded packet using the same encoder as the firmware for host interoperability checks; there is no corresponding device command.
