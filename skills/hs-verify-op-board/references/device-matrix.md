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
端口不可用、monitor 早于烧录、或只有分类标签时，输出 `ACCURACY_VERDICT=NOT_RUN`，
不得根据旧设备表猜测端口、target 或烧录方式。
