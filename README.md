# FYP radar ESP32-S3 bring-up template

This minimal ESP-IDF C++ application checks the ESP32-S3 build, flash and serial logging path. It does not read or simulate radar data. It logs `presence=UNAVAILABLE` every two seconds because the radar input has not been implemented. It does not configure or drive a lamp GPIO.

Target defaults: ESP32-S3, 16 MB flash. PSRAM is not enabled or tested by this template. The configuration uses the default UART console; connect the DevKit's USB-to-UART port for the log.

```sh
idf.py build
idf.py -p COM4 flash monitor
```

Replace `COM4` with the actual port. This is an initial bring-up check, not validation of radar sensing, detection performance, lamp control, PSRAM or the FYP requirements. Add radar framing and freshness checks before producing occupancy decisions.
