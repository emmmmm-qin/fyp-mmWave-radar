# ESP32 → PC display telemetry

## R2 (current firmware)

One ASCII record per line, terminated by LF. The reader also accepts CRLF. Fields are positional, comma-separated, with no quotes, whitespace, trailing comma, explicit point count or repeated keys. The prefix `R2` identifies this protocol and its version. This is the USB display stream, **not** the radar's native binary UART packets. No handshake or commands are required.

```text
R2,source,seq,t_ms,state[,x_m,y_m,radial_velocity_mps...]
```

Examples (illustrative, not measurements):

```text
R2,radar,0,8018,unavailable
R2,radar,41,5200,no_cloud
R2,demo,42,5300,cloud,-1,2,-1.5,0,1,0.25
```

| Field | Meaning |
| --- | --- |
| `source` | `radar` for the physical receiver path; `demo` for deliberately simulated samples. Neither indicates that a person was detected. |
| `seq` | Unsigned 32-bit frame number; zero for an unavailable board heartbeat. May wrap or skip. |
| `t_ms` | Unsigned 64-bit uptime in milliseconds. Not wall-clock or TI acquisition time. |
| `state` | `cloud` requires 1–100 point triples. `no_cloud` means a valid input frame without the supported cloud; `unavailable` means no usable frame. Neither permits point fields. |
| `x,y,v` | Finite numeric triples in sensor coordinates: metres, metres, radial m/s. Count is inferred from remaining fields. Firmware uses up to nine significant decimal digits for binary32 values, permitting scientific notation, without fixed-width padding. |

A parser must accumulate through LF (reads can split/join records), bound line length, validate every field before publishing the frame, and discard the rest of an oversized line through LF. The viewer's maximum is 16 KiB before LF. Boot/debug text remains visible in the monitor but never refreshes radar state. The monitor and parser share one read of the COM port. A display recording saves accepted packets, **not** a lossless raw serial capture.

## Migration from v1

Update the Windows viewer first: it accepts current R2 records and the old seven-field NDJSON messages (`protocol`, `v`, `source`, `seq`, `t_ms`, `state`, `points`). For example:

```json
{"protocol":"fyp-radar","v":1,"source":"radar","seq":0,"t_ms":8018,"state":"unavailable","points":[]}
```

V2 firmware emits R2 only. Historical v1 recordings remain readable in the updated viewer; the `.radar` session container is versioned independently of the USB payload. Older viewers cannot interpret v2 telemetry. Format changes do not change the BOOT double-click behaviour, input UART baud, USB console configuration, or the distinction between simulated and sensor data.
