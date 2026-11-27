# FYP：ESP32-S3 雷达网关与 Windows 2D 显示器

[English](README.md) · [固件说明](ESP32-S3/README.md) · [上位机说明](Host_Radar_Software/README.md) · [USB 数据格式](USB_PROTOCOL.md)

```text
已配置并运行的 IWRL6432BOOST ── 应用 UART ──> ESP32-S3 ── 原生 USB-C / COM ──> Windows 11
                   TI 二进制报文             解码并提取 XY / 径向速度           显示、记录、回放
```

固件、C++ 共享代码及其测试在 `ESP32-S3/`；Python 桌面程序在 `Host_Radar_Software/`。根目录不再是 ESP-IDF 工程。PC 只负责显示和记录，不参与灯控，也不从点数猜测房间是否有人。

## Windows 11 快速开始

**便携版：**双击 `mmWave-Radar.exe` 即可打开上位机，无需安装 Python、依赖或安装器。本地构建位置为 `Host_Radar_Software/dist/mmWave-Radar.exe`；`dist` 不随 Git 仓库分发。已在 Windows 11 x64 验证启动和正常退出；Windows 10 x64 尚未实测。需要从源码生成 EXE 时，请参阅[上位机打包说明](Host_Radar_Software/README.md#build-the-single-file-exe)。

**从源码运行：**在仓库根目录打开 PowerShell，使用带 Tk 的 Python 3（开发环境为 Python 3.12）：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Host_Radar_Software/requirements.txt
.\.venv\Scripts\python.exe Host_Radar_Software/radar_viewer.py
```

- **没有雷达：**选演示模式查看移动的合成点；也可连接已烧录的 ESP32，检查 USB 通信。没有 TI 数据时，实时视图应为空并提示数据不可用，而不是自动生成演示点。
- **通过 USB-C 实时显示：**用数据线连接开发板的原生 **USB** 口（不是另一侧的 USB-to-UART 口），刷新并选择 Windows 实际列出的 COM 端口。先关闭占用同一端口的 `idf.py monitor` 或串口终端。
- **雷达到货后：**先让 TI 雷达独立运行匹配的 MPD demo 和输出配置，再按[固件说明](ESP32-S3/README.md)核对 UART、波特率、电平和连接。固件接收已启动雷达的输出，不负责 TI 的刷写、CLI 配置或启动。点是传感器坐标系中的检测点，不是已确认的人体位置。

### 查看串口原始输出

在 **Connection** 连接目标 COM 口，然后打开串口监视器页签。监视器与坐标图共享连接，不需要另开终端；启动日志、异常行和遥测都能看到。新版固件输出紧凑的 ASCII 文本，例如 `R2,radar,0,8018,unavailable`。双击运行中的 ESP32 的 BOOT 可通过真实 USB 连接观察 `demo` 数据，再双击恢复 `radar`；上位机自己的 Demo 不会产生串口流量。升级顺序建议先更新上位机，再烧录固件：新版上位机兼容旧 v1 JSON 和旧录像，旧版上位机不能解析 R2。

## 构建与测试

```powershell
# 在已激活 ESP-IDF v6.1.1 的终端编译；烧录前确认实际端口
cd ESP32-S3
idf.py build
cd ..
# C++ 测试要求 CMake、Ninja 和可用的 C++17 编译器
cmake -S ESP32-S3/tests -B ESP32-S3/build/host-tests -G Ninja
cmake --build ESP32-S3/build/host-tests
ctest --test-dir ESP32-S3/build/host-tests --output-on-failure
```

[TI 源码核对记录](ESP32-S3/docs/ti_radar_research.md)限定了支持的协议版本：MMWAVE-L-SDK 05.05.04.02，xWRL6432 Motion and Presence Detection，压缩点云 TLV 301。演示、自测和 USB 状态消息都不能代替真实雷达抓包或检测性能实验。
