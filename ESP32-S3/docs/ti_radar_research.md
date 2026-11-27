# TI IWRL6432BOOST research notes

## Source and scope

The older [TI Motion and Presence Detection OOB demo page](https://software-dl.ti.com/ra-processors/esd/MMWAVE-L-SDK/05_05_00_02/exports/api_guide_xwrL64xx/MOTION_AND_PRESENCE_DETECTION_DEMO.html) describes a 52-byte frame header but shows fields that add up to 40 bytes. For the firmware and its native tests, the specific wire layout is based on the installed [TI MMWAVE-L-SDK](https://www.ti.com/tool/MMWAVE-L-SDK) **05.05.04.02** sender and cross-checked against the installed Radar Toolbox **4.30.00.06** Applications Visualizer. The actual radar firmware and configuration have not been confirmed.

| Wire detail | Evidence in the installed SDK |
| --- | --- |
| 40-byte little-endian header; sync word, platform `0x000A6432` and version `0x05050402` | `source/motion_detect.h` (`MmwDemo_output_message_header_t`); `source/motion_detect.c` (`mmwDemo_TransmitProcessedOutputTask` fills the header and transmits `sizeof` it); `source/mmw_cli.h` (version macros). |
| TLV prefix is 8 bytes, length excludes prefix; packet is rounded up to 32 bytes | `source/motion_detect.c` accounts separately for prefix and payload, calculates `totalPacketLen`, then writes the padding. Padding contents are not checked. |
| Compressed point cloud is TLV `301`; 20-byte scale/count block plus 10 bytes per point, maximum 100 points | `source/motion_detect.h` defines the ID, records and capacity; `source/dpc/dpc.c` fills scale factors and orders major points before minor points; `source/motion_detect.c` sends the cloud only with detections and point-cloud mode `2`. |
| The supplied EVM profiles select compressed output | `profiles/xwrL64xx-evm/PresenceDetect.cfg` and `MotionDetect.cfg` both start `guiMonitor` with `2`. |

SDK paths in the table are relative to `examples/mmw_demo/motion_and_presence_detection`. The Toolbox cross-check used `tools/visualizers/Applications_Visualizer/common/{parseFrame.py,parseTLVs.py,tlv_defines.py}`. The prototype does not include or depend on TI source files at build time.

## What is implemented

`core/ti_mpd_packet.*` decodes a single complete packet for the verified source layout, without UART or ESP-IDF dependencies. It exposes the frame number, reported total and major/minor point counts, coordinates in metres, radial velocity in m/s, and SNR/noise in dB. Other TLVs are skipped if their lengths fit; their contents are not validated. A valid packet may have no compressed cloud even with a non-zero reported count. Neither an absent cloud nor a frame reporting zero detections is sufficient to declare `VACANT`. Tests use hand-built synthetic byte arrays, not sensor recordings.

The ESP32-S3 firmware now links this decoder into an RX-only UART stream receiver (`core/radar_stream.*`). It bounds candidate length and assembly time, discards invalid input, and publishes only valid decoded frames or unavailable heartbeats via native USB stdout. The PC receives sensor-frame X/Y and radial velocity, not person positions. The `core/presence.*` self-test is still separate: neither live packets nor missing packets are mapped to occupied/vacant. See [firmware setup and limits](../README.md).

## Before connecting hardware

Record the EVM revision, exact firmware, SDK and profile. After confirming the board and UART setup against the applicable guide, run the TI Visualizer and capture representative UART packets, including frames with zero detections. Compare those bytes and decoded points with the pinned source/Visualizer, then confirm packet sizes, UART data baud, inter-frame intervals and recovery on the real link. Host fixtures and a successful firmware build do not establish that the physical radar matches this profile. No lamp control or occupancy algorithm is part of this telemetry path.
