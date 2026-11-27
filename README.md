# FYP radar ESP32-S3 bring-up template

This ESP-IDF C++ application contains a protocol-independent presence-state prototype. On startup, it runs a labelled synthetic self-test using a separate state machine. The live state logs `presence=UNAVAILABLE` every two seconds: there is no live radar input, position estimate or lamp GPIO output.

Target defaults: ESP32-S3, 16 MB flash. PSRAM is not enabled or tested by this template. The configuration uses the default UART console; connect the DevKit's USB-to-UART port for the log.

```sh
idf.py build
idf.py -p COM4 flash monitor
```

Replace `COM4` with the actual port. This does not validate radar sensing, detection performance, lamp control, PSRAM or the FYP requirements. The state-machine timing and confirmation counts are test-only placeholders, not measured radar parameters.

## Host tests

With CMake, Ninja and a C++17 compiler installed:

```sh
cmake -S tests -B build/host-tests -G Ninja
cmake --build build/host-tests
ctest --test-dir build/host-tests --output-on-failure
```

The tests cover the presence state machine and the offline TI packet decoder using synthetic observations and byte arrays, not radar captures.

## Offline TI packet decoding

`core/ti_mpd_packet.*` decodes the compressed point cloud (TLV `301`) from one complete xWRL6432 Motion and Presence Detection packet for MMWAVE-L-SDK `05.05.04.02`. It returns sensor-frame coordinates, radial velocity, SNR/noise and major/minor point counts. Missing point data is not a vacancy decision.

The decoder is not wired into the ESP32 firmware. It does not read UART, find packet boundaries in a stream, or infer occupancy. See the [TI radar notes](docs/ti_radar_research.md) for the source checks and what to verify when the radar arrives.
