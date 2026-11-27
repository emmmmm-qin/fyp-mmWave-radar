# Synthetic state-machine verification — 2026-11-21

## Scope

No IWRL6432BOOST radar was connected. The normalized boolean observations and the test configuration (1000 ms stale interval, 2 occupied and 3 vacant confirmation samples) are synthetic test fixtures, not radar captures or performance targets. The board self-test runs on a separate state-machine instance from the live monitor.

## Host test

On Windows, GNU C++ 14.2.0, CMake and Ninja built the test executable. `ctest --test-dir build/host-tests --output-on-failure` reported `1/1 passed`. Checks cover unavailable at startup, confirmation counts, freshness boundaries, missing/invalid inputs, duplicate and regressing timestamps, and invalid configuration. The single CTest case contains multiple checks.

## ESP32-S3 test

- ESP-IDF v6.1.1; ESP-IDF MCP reported successful build and flash to COM4.
- Approximately eight seconds of UART output at 115200 baud included:

```text
I (254) fyp: FYP: radar input not implemented; live presence remains unavailable
I (254) fyp: SYNTHETIC SELF-TEST PASS (not radar data)
I (254) fyp: LIVE heartbeat=1 presence=UNAVAILABLE radar=not_connected
I (2264) fyp: LIVE heartbeat=2 presence=UNAVAILABLE radar=not_connected
I (4264) fyp: LIVE heartbeat=3 presence=UNAVAILABLE radar=not_connected
I (6264) fyp: LIVE heartbeat=4 presence=UNAVAILABLE radar=not_connected
I (8264) fyp: LIVE heartbeat=5 presence=UNAVAILABLE radar=not_connected
```

This demonstrates the on-board synthetic self-test and live unavailable reporting in this brief run. It does not demonstrate radar communication, physical occupancy, position, performance, long-term stability, PSRAM, a lamp, or final project requirement compliance.
