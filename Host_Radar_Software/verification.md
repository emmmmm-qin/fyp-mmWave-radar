# Windows viewer integration check — 2026-11-27

| Check | Result and scope |
| --- | --- |
| Windows viewer | Python 3.12, Tk 8.6, pyserial 3.5: 8 unittest cases passed, including a real Tk window, serial loopback, parser recovery, recording/replay and disconnect behaviour. |
| Portable firmware logic | CTest 2/2 passed, including split/coalesced TI packets, invalid lengths, resynchronization, synthetic point decoding and host telemetry. |
| Cross-language contract | The C++ encoder emitted frame 42 from a synthetic TI packet. The Python viewer parser received it in seven-byte chunks and decoded both expected XY/velocity triples: `[-1,2,-1.5]` and `[0,0,16383.5]`. The latter intentionally exercises the encoded velocity boundary, not a plausible human speed. |
| ESP32 → PC | ESP-IDF v6.1.1 build succeeded; flashed the identified ESP32-S3 N16R8 over native USB Serial/JTAG on COM5. The Tk viewer opened COM5 and accepted three successive `source=radar`, `state=unavailable`, `points=[]` messages at uptime 9018, 10018 and 11018 ms. It rendered no points and released the port after testing. |

The TI radar was not connected. Only the ESP32-to-PC status link was tested on physical hardware; cloud formatting and display were tested with synthetic inputs. No real radar UART reception, accuracy, throughput under load, presence detection or Raspberry Pi operation is claimed.
