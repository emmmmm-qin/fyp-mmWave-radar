# FYP 雷达 ESP32-S3 启动调试模板

这个 ESP-IDF C++ 应用包含一个与雷达协议无关的状态机原型。启动时，程序使用独立的状态机执行明确标注为合成数据的自测。实时状态每两秒记录一次 `presence=UNAVAILABLE`：尚未实现雷达输入、TI 报文解析、位置估计或灯 GPIO 控制。

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

测试输入是合成观测值，不是真实 TI 雷达数据。文档来源、协议疑点和下一步硬件验证见 [TI 雷达调研记录](docs/ti_radar_research.md)。