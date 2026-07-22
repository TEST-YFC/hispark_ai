# 设备支持

## WS63 / Hi3863（全自动）

| 项目 | 值 |
|------|------|
| 芯片 | WS63 / Hi3863 |
| 架构 | RISCV |
| 开发板 | 小熊派标准板 |
| 烧录工具 | BurnTool_H3863 (`Burntool.exe`) |
| 控制芯片 | CH340G |

### 接线

| CH340G | Hi3863 | 功能 |
|--------|--------|------|
| DIR (→ DTR) | Pin 6 | 芯片复位 |
| RTS | Pin 22 | 启动模式选择 (LOW=下载模式) |
| GND | GND | 共地 |

### 烧录时序

1. CH340G RTS=LOW (GPIO0=下载模式)
2. CH340G DTR=HIGH → LOW (复位脉冲，芯片进入下载模式)
3. Burntool 连接并烧录固件
4. CH340G RTS=HIGH (GPIO0=正常模式)
5. CH340G DTR=HIGH → LOW (复位脉冲，芯片正常运行)
