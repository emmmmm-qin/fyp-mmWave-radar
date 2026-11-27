# Windows radar viewer

From the repository root, using a Windows Python 3 installation with Tkinter:

```powershell
py -m pip install -r Host_Radar_Software/requirements.txt
py Host_Radar_Software/radar_viewer.py
```

There are no CLI options. The viewer starts disconnected. **Synthetic demo** runs a moving point without discovering or opening any COM port. **LIVE** is the serial transport, not a guarantee of real detections: check the packet **Source** (`radar` or `demo`). **REPLAY** reads a file only. Stop one input before starting another; there is no automatic demo fallback.

For live use, select **Refresh**, select or enter a COM port, choose the producer's baud rate (default 115200, 8N1), then **Connect**. The viewer expects the host protocol below, not raw TI binary output. It polls every 20 ms, reads at most 8192 bytes per poll with `timeout=0`, and never writes to the port. Disconnect or an input error closes the source and clears the canvas.

The origin is the radar. X increases rightward and Y forward/upward, with equal metres per pixel. **Range ±m** changes both axis limits; points outside the square are not drawn but remain in the packet count. Hover over a visible point for X, Y and radial velocity. **Frames** counts accepted packets in the current input session. **Display seq**, **Source**, **Points** and state describe the displayed frame. Pause freezes the picture, not reception, frame counting or recording. Resume displays the newest packet. Empty frames, explicit loss of cloud, disconnect, and 1.5 seconds without a valid frame clear old detections even during pause. The log reports connection, recording, replay and parser errors; **Clear log** clears messages only.

## Host protocol v1

One ASCII JSON object per LF-terminated line (CRLF accepted), at most 16 KiB before the LF. All seven fields are required, with no extra or duplicate keys. Example:

```json
{"protocol":"fyp-radar","v":1,"source":"radar","seq":42,"t_ms":1234,"state":"cloud","points":[[-0.25,1.5,-0.2]]}
```

- `protocol` must be `fyp-radar`; `v` must be the integer `1`.
- `source`: `radar` or `demo`. `seq`: unsigned 32-bit integer. `t_ms`: nonnegative integer producer timestamp. Neither arrival order nor replay timing is inferred from these counters.
- `state`: `cloud`, `no_cloud`, or `unavailable`. `points`: 0–100 arrays of exactly three finite numbers `[x_m, y_m, radial_velocity_mps]`; booleans are not numbers. Both non-cloud states require `[]`.
- Startup text is ignored. Invalid packet lines are logged and do not refresh the last-valid timer. After an oversized line the parser discards through LF and resumes.

## Record and replay

Choose **Record / Stop** during LIVE or synthetic demo to save a `.radar` session. Only complete accepted packets are recorded; their original payload and source are preserved. Stop recording explicitly or disconnect to close the file. Each binary-written ASCII session begins with `FYP-RADAR-SESSION 1` and LF, followed by rows of `host_offset_ms<TAB>original_packet<LF>`. Offsets are monotonic host receipt times relative to recording start, including any initial silence. **Replay session** uses these offsets at normal speed, streams the file incrementally, and never opens a serial port. Packets received in one serial poll may share a timestamp. Equal-time frames are counted individually, but only the newest is painted per UI poll. EOF clears the display. Invalid session rows stop replay with a log message.

## Verify without hardware

```powershell
py -B -m unittest discover -v -s Host_Radar_Software
```

The suite includes an actual Tk window, an in-memory pyserial `loop://` connection, and emulated unplug/replay. It does not enumerate or open physical serial ports. GUI tests require a desktop display.

After building the C++ tests as described in the repository README, check the firmware serializer against the actual viewer line parser using the two-point binary TI fixture:

```powershell
py Host_Radar_Software/check_usb_contract.py ESP32-S3/build/host-tests/ti_mpd_packet_test.exe
```
