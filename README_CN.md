# FYP 雷达 ESP32-S3 启动调试模板

这个最小的 ESP-IDF C++ 应用程序检查 ESP32-S3 的构建、烧录和串口日志记录路径。它不读取或模拟雷达数据。由于尚未实现雷达输入，它每两秒记录一次 `presence=UNAVAILABLE`。它不配置或驱动灯 GPIO。

目标默认配置：ESP32-S3，16 MB flash。此模板未启用或测试 PSRAM。该配置使用默认 UART 控制台；请连接 DevKit 的 USB-to-UART 端口以获取日志。

```sh
idf.py build
idf.py -p COM4 flash monitor
```

将 `COM4` 替换为实际端口。这是一次初始启动调试检查，不是对雷达感测、检测性能、灯控制、PSRAM 或 FYP 要求的验证。在生成占用判定之前，请添加雷达数据分帧与新鲜度检查。