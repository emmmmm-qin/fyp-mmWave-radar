# TI IWRL6432BOOST research notes

## Scope and source

These notes are preparatory, not verification against a physical radar. The source reviewed is TI's [xWRL6432 MMWAVE-L-SDK Motion and Presence Detection OOB Demo](https://software-dl.ti.com/ra-processors/esd/MMWAVE-L-SDK/05_05_00_02/exports/api_guide_xwrL64xx/MOTION_AND_PRESENCE_DETECTION_DEMO.html). The rendered page identifies itself as **05.05.00.00**, although the URL contains `05_05_00_02`. The user's eventual firmware and SDK version are not established.

The demo documentation describes a single UART for configuration and data, with one little-endian TLV packet per radar frame. Enabled outputs depend on configuration. The example has different presence and motion profiles. PresenceDetect uses minor-motion processing; MotionDetect supplies points for a tracker. The documented point formats include floating-point Cartesian coordinates and radial velocity, or a compressed format with units and separate major/minor counts. There is also a packed zone-presence output. These describe the cited demo, not all IWRL6432 firmware.

## Unresolved protocol details

The documentation says the frame header is **52 bytes**, but its displayed structure lists four 16-bit magic words and eight 32-bit fields (40 bytes in total). Do not assume a header size or parser compatibility from this alone. Obtain and inspect the exact version's transmitting source and an independently captured byte stream before committing a wire format. TLV identifiers, actual length semantics, zero-point frames, enabled outputs, padding, frame timing, CLI startup and serial port settings must similarly be checked for the chosen firmware/configuration. No hardware communication has been tested.

## What the current code does

`core/presence.*` is a small protocol-independent, deterministic state machine operating on already-normalized valid/invalid observations. Its sample parameters are placeholders for tests, not radar or FYP performance requirements. It cannot transform TI point clouds into presence or position. Synthetic inputs are deliberately isolated from the live monitor; no radar, position estimate, UART parser, or lamp output is implemented.

Next, once the radar arrives: record the exact firmware, SDK, profile and output configuration; test it with TI's tools; capture real UART traffic; resolve header and TLV behavior against that version's source; build parser fixtures from documented and real captures; verify signal levels, power, wiring and UART configuration against the applicable EVM guide before connecting the ESP32. Then integrate the parser, freshness policy and portable processing core without treating missing input as vacancy.
