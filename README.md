# FYP radar ESP32-S3 bring-up template

This ESP-IDF C++ application contains a protocol-independent presence-state prototype. On startup, it runs a clearly labelled synthetic self-test using a separate state machine. The live state logs `presence=UNAVAILABLE` every two seconds: there is no radar input, TI packet parser, position estimate or lamp GPIO implementation.

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

The tests use synthetic observations; they are not TI radar captures. See [TI radar research notes](docs/ti_radar_research.md) for the chosen documentation, unresolved packet-format questions and the future hardware bring-up steps.
