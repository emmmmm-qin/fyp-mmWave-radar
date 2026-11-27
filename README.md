# FYP radar gateway and 2D viewer

[中文](README_CN.md) · [Firmware](ESP32-S3/README.md) · [Windows viewer](Host_Radar_Software/README.md) · [USB telemetry format](USB_PROTOCOL.md)

```text
Running IWRL6432BOOST MPD demo → radar application UART → ESP32-S3 decoder → native USB-C COM port → Windows 11 viewer
```

`ESP32-S3/` contains the ESP-IDF project, portable C++ core and native tests. `Host_Radar_Software/` contains the Python desktop application. The repository root is no longer an IDF project. The PC displays and records sensor-frame detections; point count is not a presence decision.

## Run the viewer on Windows

**Portable EXE:** Double-click `mmWave-Radar.exe`. No installer, Python installation or pip dependencies are needed on the viewing PC. The local build is at `Host_Radar_Software/dist/mmWave-Radar.exe`; this generated directory is not included in a Git checkout. Launch and normal exit were verified on Windows 11 x64; Windows 10 x64 has not yet been tested. See the [viewer packaging instructions](Host_Radar_Software/README.md#build-the-single-file-exe) to rebuild it.

**From source:** From the repository root, with a Tk-enabled Python 3 installation (developed using Python 3.12):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Host_Radar_Software/requirements.txt
.\.venv\Scripts\python.exe Host_Radar_Software/radar_viewer.py
```

Select **Demo** to try the viewer without hardware. For live data, connect the DevKit's **native USB** connector using a data cable, close any serial monitor, refresh the ports and select the enumerated COM device. With the firmware running but no radar input, the viewer should receive unavailable status, not synthetic points. Replay and recordings are display telemetry, not raw TI binary captures.

### Inspect the serial output

Connect in **Connection**, then open the serial monitor tab. It uses the same live COM handle as the plot, so you can inspect boot messages, malformed lines and telemetry without starting another terminal. Firmware v2 emits compact ASCII records, for example `R2,radar,0,8018,unavailable`. Double-click BOOT on the running board to test the USB path with `demo` records; double-click again to return to radar input. The PC-only Demo is not serial traffic. Update the viewer before flashing v2: the new viewer also accepts old v1 JSON firmware and recordings, but old viewers cannot decode R2.

## Build the firmware / run C++ tests

```powershell
# In an activated ESP-IDF v6.1.1 terminal
cd ESP32-S3
idf.py build
cd ..
# With CMake, Ninja and a C++17 compiler on PATH
cmake -S ESP32-S3/tests -B ESP32-S3/build/host-tests -G Ninja
cmake --build ESP32-S3/build/host-tests
ctest --test-dir ESP32-S3/build/host-tests --output-on-failure
```

The radar must already be configured and transmitting the supported xWRL6432 MPD profile (MMWAVE-L-SDK 05.05.04.02, compressed cloud TLV 301). See the [firmware setup](ESP32-S3/README.md) and [TI research notes](ESP32-S3/docs/ti_radar_research.md) before connecting the radar UART. Neither a demo nor an ESP32 heartbeat validates the real radar, position accuracy or occupancy detection.
