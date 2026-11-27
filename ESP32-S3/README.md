# ESP32-S3 radar telemetry bridge

By default the firmware listens to an **externally configured and started** TI radar. It never sends CLI commands or decides occupancy. Without valid input it reports `unavailable`, not an empty-room reading.

## Open the Windows viewer

Start the portable `mmWave-Radar.exe` on the PC, or [run the viewer from source](../Host_Radar_Software/README.md). Both use the same R2 serial protocol. The EXE is **not** a firmware image: packaging or updating the viewer does not flash the ESP32. Close any other serial monitor before selecting the board's native USB COM port under **Connection**.

## Validate over USB without a radar

Connect the Windows viewer to the ESP32's native USB COM port (do not start the PC's Synthetic demo). After normal startup, quickly press and release **BOOT twice**. The transport remains `LIVE`, but `Source` changes from `radar` to `demo`. The board sends about five packets per second in a repeating 12-second cycle: **4 s moving point**, **4 s valid frame without a cloud**, **4 s data unavailable**. Record/replay preserves `source=demo`.

Double-click BOOT again to resume radar input; if disconnected, expect `source=radar`, `state=unavailable`. No mode is saved across resets. Both clicks must be short (≤450 ms each), with releases within 550 ms; GPIO0 is debounced for 30 ms. Do not hold BOOT while powering up or pressing EN/RESET: that selects the [ROM download mode](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/advanced-topics/boot-mode-selection.html). The test exercises the output and viewer, not the radar receiver or occupancy performance.

## Connect and configure

1. Use a compatible xWRL6432 Motion and Presence Detection image/profile (see [supported wire format](docs/ti_radar_research.md)). Configure it separately to emit compressed points (`guiMonitor` point-cloud mode `2`). Confirm the **actual data baud** after sensor start; it need not equal the CLI baud.
2. With power off, connect the verified **3.3 V logic** radar data TX to ESP32-S3 **GPIO18** and connect grounds. Use level translation for other logic levels; never feed RS-232 or 5 V into an ESP GPIO. Leave radar RX, ESP TX, and flow-control lines disconnected. Power each board according to its own guide. Check the actual board schematic for pin conflicts.
3. Open an ESP-IDF terminal in this directory (build verified with v6.1.1). For a new configuration run `idf.py set-target esp32s3`, then `idf.py menuconfig` if needed and `idf.py build`. Under **FYP radar input**, defaults are UART1, RX GPIO18, **115200 8N1**, no flow control. Set baud to match the radar, e.g. 1250000 if that is its configured output. Allowed controllers are UART1/2 and RX pins GPIO4–18, a conservative subset excluding USB, straps and flash/PSRAM pins. This is not a guarantee that every allowed pin is free on your carrier. Defaults assume 16 MB flash; adapt for other modules. If reusing `sdkconfig`, ensure **USB Serial/JTAG Controller** is the primary console (not USB OTG CDC or UART).
4. On a board running the firmware, use a data cable on the **native USB** connector (GPIO19 D−, GPIO20 D+), not the CH343/USB-UART port used in the historical bring-up. Open its COM port in one reader at a time. USB line speed is independent of the radar baud. Ignore non-protocol boot/self-test lines. See [Espressif USB Serial/JTAG console](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-guides/usb-serial-jtag-console.html).

## What the host receives

One compact ASCII line per update: `R2,source,seq,t_ms,state[,x,y,v...]` followed by LF. No repeated JSON keys, point brackets or count field. Source is `radar` or `demo`. Valid radar packets use the TI frame number and ESP uptime in milliseconds. `cloud` has 1–100 coordinate/velocity triples; `no_cloud` means a valid packet without the supported cloud. Neither `no_cloud` nor `unavailable` has trailing point fields. During startup/silence, `unavailable` uses sequence zero: immediately while waiting, then once a second, beginning two seconds after the last valid packet. Invalid input does not refresh liveness. View the actual lines in the Windows serial monitor; boot/self-test diagnostics remain separate text lines. See the [v2 protocol and migration notes](../USB_PROTOCOL.md).

The receiver handles fragmented/concatenated packets and scans rejected candidates for the next sync. Maximum packet size is 8192 bytes including padding. Partial candidates expire after 250 ms without bytes or 2 s total. Larger optional radar outputs (e.g. heatmaps) may exceed this limit; disable them or validate and revise the cap. A separate, lower-priority stdout task takes the latest sample from a one-slot mailbox; under USB backpressure old samples may be skipped. This is a live display, not lossless recording. Host software should reject malformed/partial lines and expire stale displays even if USB disconnects. The boot self-test is diagnostic text only.

## Native verification (no device)

```
cmake -S tests -B build-host
cmake --build build-host
ctest --test-dir build-host --output-on-failure
```

For multi-config generators specify `--config Debug` on build and `-C Debug` on CTest. `ti_mpd_packet_test --emit-fixture` prints one synthetic decoded packet using the same encoder as the firmware for host interoperability checks; there is no corresponding device command.
