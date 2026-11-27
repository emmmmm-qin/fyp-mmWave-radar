# ESP32 → PC telemetry v1

This is a display protocol, not the TI binary UART format. The ESP32 obtains points from the pinned xWRL6432 MPD decoder. A Windows client opens the board's **native USB Serial/JTAG COM port** and consumes UTF-8/ASCII JSON objects, one per newline (LF or CRLF). Ignore console text and unsupported versions. No commands or acknowledgements are required from the PC.

Synthetic illustration of a received frame (not a measurement):

```json
{"protocol":"fyp-radar","v":1,"source":"radar","seq":42,"t_ms":5300,"state":"cloud","points":[[-0.25,1.5,-0.12],[0.11,1.4,0.08]]}
```

| Field | Meaning |
| --- | --- |
| `protocol`, `v` | Literal `fyp-radar` and integer `1`. |
| `source` | `radar` for the ESP32 receive path, `demo` for explicitly generated samples. The viewer separately identifies playback. |
| `seq` | Unsigned 32-bit TI frame number when available; `0` in an unavailable heartbeat. Gaps can occur. |
| `t_ms` | Nonnegative integer milliseconds since ESP32 startup (demo uses its own clock), not wall time or TI acquisition time. |
| `state` | `cloud`: decoded compressed points. `no_cloud`: valid packet without this point payload. `unavailable`: no current usable radar frame. |
| `points` | Up to 100 triples `[x_m, y_m, radial_velocity_mps]` in sensor coordinates. Finite numbers; an empty array is required for `no_cloud` and `unavailable`. |

The viewer plots X horizontally and Y forward, in metres; it does not infer identity, occupancy or a person's position. A heartbeat means the USB endpoint is alive, **not** that the radar is working. On stale input or disconnect do not continue presenting old points as live. This display protocol intentionally omits Z, SNR/noise, full TI TLVs and raw ADC samples; a saved viewer session is not a raw radar capture.
