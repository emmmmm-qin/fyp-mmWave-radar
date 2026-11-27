# FYP 雷达 ESP32-S3 启动调试模板

这个 ESP-IDF C++ 应用包含一个与雷达协议无关的状态机原型。启动时，程序用独立的状态机执行合成自测。实时状态每两秒记录一次 `presence=UNAVAILABLE`：尚未实现实时雷达输入、位置估计或灯 GPIO 控制。

目标默认配置：ESP32-S3，16 MB flash。此模板未启用或测试 PSRAM。该配置使用默认 UART 控制台；请连接 DevKit 的 USB-to-UART 端口以获取日志。

```sh
idf.py build
idf.py -p COM4 flash monitor
```

将 `COM4` 替换为实际端口。本测试不能验证雷达感测、检测性能、灯控制、PSRAM 或 FYP 要求。状态机里的时限和确认帧数只用于测试，并非依据实际雷达测得的参数。

## PC 端测试

安装 CMake、Ninja 和 C++17 编译器后运行：

```sh
cmake -S tests -B build/host-tests -G Ninja
cmake --build build/host-tests
ctest --test-dir build/host-tests --output-on-failure
```

测试覆盖状态机和 TI 离线报文解码，使用合成观测值和字节数组，不是真实雷达抓包。

## TI 报文离线解码

`core/ti_mpd_packet.*` 可从一包完整的 xWRL6432 Motion and Presence Detection 报文中解码压缩点云（TLV `301`），目前仅针对 MMWAVE-L-SDK `05.05.04.02`。输出包括传感器坐标系中的坐标、径向速度、信噪比与噪声、以及 major/minor 点数。没有点云不等于无人。

解码器尚未接入 ESP32 固件，不读取 UART、不从字节流中寻找帧边界，也不判断有人或无人。源码依据和到货后需要验证的事项见 [TI 雷达调研记录](docs/ti_radar_research.md)。