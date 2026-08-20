# 真板与串口条件

本文只核对板端精度验证需要的设备身份和串口证据。固件 target 以
`hs-dev-build`/`fbb describe --json` 为准，烧录端口和结果以
`hs-dev-flash`/`fbb flash --json-summary` 为准。本 skill 不描述或驱动底层烧录后端。

## WS63 / Hi3863

开始精度验证前记录：

| 字段 | 要求 |
|---|---|
| board/chip | workflow 或 fbb 返回的真实设备标识 |
| target | 本轮固件使用的 fbb target |
| firmware | 已成功烧录的绝对 fwpkg 路径 |
| serial port | 本轮 monitor 使用的端口 |
| baudrate | 项目 sample 明确要求的波特率，常见值为 115200 |
| flash evidence | 本轮 `FLASH_VERDICT=PASS` 或 fbb JSON `success=true` |
| monitor time | 晚于本轮烧录完成时间 |

串口工具必须保存完整原始文本，包含本轮启动标志、case 身份、机器可读 shape 和完整输出 Tensor。

## 端口探测与证据

Windows 的 `Win32_SerialPort`/WMI 可能漏报 CH340/CH341 等 USB-UART（例如设备实际为
`USB-SERIAL CH340 (COM12)`，但 WMI 只返回 Intel AMT SOL）。烧录前必须运行
`hs-verify-op-board/scripts/probe_serial_ports.py`，交叉记录 `.NET SerialPort.GetPortNames()`、
`HKLM:\\HARDWARE\\DEVICEMAP\\SERIALCOMM` 和有界的 `pnputil` 查询；每个来源的结果、错误、
端口、设备描述/VID/PID 和时间写入 `serial_probe.json`。单一来源为空不能推出“没有开发板”。
CH340/CH341、CP210x、FTDI、USB-SERIAL 只构成候选，最终仍以 `hs-dev-flash`/`fbb flash`
返回的真实设备身份、`success=true` 和本轮串口输出为准。多个候选或来源冲突时必须列出证据并
请求用户选择，不能猜测控制口。
端口不可用、monitor 早于烧录、或只有分类标签时，输出 `ACCURACY_VERDICT=NOT_RUN`，
不得根据旧设备表猜测端口、target 或烧录方式。
