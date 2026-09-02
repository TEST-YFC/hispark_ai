# Board guardrails

目录：

- [红线](#红线)
- [完成判据](#完成判据)
- [资源索引](#资源索引)

以下内容从入口按需下沉；失败措辞、完成判据和资源所有权保持不变。

## 红线

1. 完整模式下用户未明确提供固件SDK源码位置，不得开始SDK写入、构建或烧录。
2. 没有当轮 Host PASS 和同一 case GT 不做板端精度签收。
3. 烧录成功不等于精度成功；只有完整 Tensor 比对可产生 `ACCURACY_VERDICT=PASS`。
4. 不直接调用 BurnTool 或任何绕过统一入口的烧录脚本；烧录统一交给 `hs-dev-flash`/`fbb flash`。
5. 不自己实现另一套固件构建器；构建统一委托 `hs-dev-build`/`fbb build`，但不能省略构建前接线。
6. 不手填预期张量、余弦值，不复用跨轮GT/monitor，不调低阈值。
7. 不因“硬件公差”“串口噪声”放行精度失败；先用原始输出证明根因。
8. 不以只有平铺数值、缺少shape元数据的串口输出签收；相同元素数不代表输出shape正确。
9. 不修改Host用例、能力清单或算子源码来让板测变绿。
10. 不允许以一个或少数代表case的PASS签收完整算子；expected分母只能来自Host manifest。
11. 不允许只汇报总PASS；最终用户消息必须逐行列出实际执行的case/mode和各自状态。
12. 固件生成、接线、clean build和内容检查只属于“固件构建验证”，不能写成“板测通过”或
    “验证全部通过”；没有逐行烧录、当轮串口完整Tensor和精度比对时，板测状态必须是NOT_RUN。

## 完成判据

只有以下条件同时成立，才输出：

```text
ACCURACY_VERDICT=PASS
```

- `board_expected_matrix.json`每行在本轮Host summary中明确PASS；
- 每行的`BOARD_SDK_GATE`、`SAMPLE_PREP_GATE`、`BOARD_WIRING_GATE`与
  `FIRMWARE_CONTENT_GATE`均PASS；
- 每行固件身份与该case的模型、输入、模式一致；
- 每行`FLASH_VERDICT=PASS`；
- 每行本轮串口完整Tensor已保存；
- `board_accuracy.py`对每行的每个Tensor均达到固定阈值；
- `board_matrix_report.py`输出`expected=executed=pass`、`fail=not_run=0`和
  `BOARD_MATRIX_GATE=PASS`。

否则输出`ACCURACY_VERDICT=FAIL`或`ACCURACY_VERDICT=NOT_RUN`，并列出所有case状态、缺失证据
或失败owner。`BOARD_MATRIX_GATE`必须与该终态一致地输出`FAIL`或`NOT_RUN`，不能把未执行写成
普通FAIL，也不能把一条NOT_RUN记录算作executed。FAIL/NOT_RUN时不得使用“板测完成”
“端到端通过”“已完成迁移和验证”“已完成开发和验证”“验证通过”“全部通过”或✅等完成语义；
即使1/N通过也只能报告“已执行1/N”，不能报告算子上板验证完成。

## 资源索引

| 资源 | 用途 |
|---|---|
| `scripts/board_accuracy.py` | 当前唯一板端 Tensor 精度判定入口 |
| `scripts/board_matrix_report.py` | 对账Host期望分母与逐case板测结果，生成机器/人可读全矩阵报告 |
| `scripts/probe_serial_ports.py` | 有界重试交叉探测 Windows/WSL 串口并保存每次来源、错误和候选设备回执；避免重插竞态和单一 WMI 假阴性 |
| `chips/ws63/scripts/prepare_sample.py` | 从模型元数据和Host二进制输入确定性生成一次性、多dtype、多输入/输出Sample |
| `chips/ws63/scripts/check_python_deps.py` | 在模型解析前检查本轮 framework 所需 Python 模块是否可导入并输出版本 |
| `chips/ws63/scripts/build_micro.py` | 固定生成FP32/INT8配置，运行converter和Micro CMake，冻结两份模型库与receipt |
| `chips/ws63/scripts/integrate_sdk.py` | 固定安装adaptor、模型库并接入WS63 CMake/target；拒绝静默覆盖差异文件 |
| `chips/ws63/scripts/verify_wiring.py` | 构建前机械核对Sample、两份库、adaptor和CMake/Kconfig消费点 |
| `chips/ws63/scripts/verify_firmware.py` | 构建后机械核对Sample对象、最终map符号和完整fwpkg新鲜度 |
| `chips/ws63/references/device.md` | 核对 WS63 串口和设备信息；非WS63不得套用本接入规范 |
| `chips/ws63/references/troubleshooting.md` | 读取串口和板端结果异常时 |
| `chips/ws63/references/sdk-integration.md` | 必须完整读取；规定Micro模型、adaptor、Sample、CMake/Kconfig和固件接入细节 |
