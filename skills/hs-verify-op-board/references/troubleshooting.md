# 板端精度故障分流

本页只处理“固件已构建、已烧录”之后的串口 Tensor 和精度问题。构建失败回到
`hs-dev-build`，烧录失败回到 `hs-dev-flash`；不得从本 skill 直接调用 BurnTool、
旧 HTTP 烧录服务或历史脚本。

## 没有串口输出

1. 核对 workflow 交付的 `target`、串口端口、烧录 JSON 和本轮 monitor 时间。
2. 确认 monitor 包含本次烧录后的启动标志；没有启动标志时不能复用旧日志。
3. 确认 sample 已接入所选 Host PASS case 的模型和输入，并会打印完整 Tensor。
4. 启动失败或模型未接入归 workflow 的固件/sample 接线，不归精度脚本。

## Tensor 不完整或无法解析

- 保留原始 monitor，不手抄、不截取前十项、不只保留分类标签。
- 核对输出 Tensor 数量、元素数和 shape 是否与同轮 `gt/output*.npy` 一致。
- 串口截断时增大 monitor 的行数/时限后重新采集，不修改 GT 或解析结果。
- 若固件只打印摘要，回流 sample 接线以输出完整 Tensor。
- `[AI_MCU] Data:` 前必须有机器可读的 `[AI_MCU] Shape: [d1,d2,...]`；缺失时
  `board_accuracy.py` 输出 `SHAPE_UNVERIFIED`，不得把平铺值相同当成 shape 已验证。

## Host PASS、Board FAIL

1. 用 `board_accuracy.py` 保存每个 Tensor 的 shape、元素数和余弦证据。
2. 核对模型、输入、GT、量化模式和固件来自同一 case、同一轮。
3. shape/数量不同优先归固件模型或 sample 接线；数量一致但数值错误，再由 workflow
   根据首个差异回流板端接入或算子实现。
4. 不降低阈值，不以硬件公差或串口噪声直接放行。

## 记录格式

```text
case=<framework>/<case-id>
firmware=<absolute path>
monitor=<absolute path>
gt_dir=<absolute path>
mode=<fp32|int8>
first_failure=<raw evidence>
owner=<workflow-stage5|hs-dev-flash|hs-dev-op-implement|hs-verify-op-board>
```
