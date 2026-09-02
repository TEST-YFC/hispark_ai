---
name: hs-verify-op-board
description: >-
  Prepare WS63 MindSpore Lite Micro operator board integration and verify the complete Host-derived
  real-board case matrix. Use when the user explicitly names hs-verify-op-board, asks only for WS63
  operator board preparation/accuracy, or hs-workflow-op-development routes its board stages here.
  Require the user-provided firmware SDK source location, replay every Host-PASS framework/case/mode,
  generate and cross-compile each Micro model, generate the OH_AI sample, verify wiring, hand build/flash
  execution and results back to the top-level workflow, collect complete serial tensors, and report per-case plus
  aggregate accuracy. Other chips require their own chip-specific integration reference; never reuse
  WS63 paths by analogy. Do not use this skill for source implementation or Host test design. 中文触发包括“只做板端精度”“板端精度”“真板验证”“烧录并验证”“使用 hs-verify-op-board”；
  仅源码或仅 Host 请求不触发本 Skill。
---

# 算子真板精度验证

本 Skill 负责把本轮 Host 已通过的板端适用矩阵逐行接入固件并核对真实板输出。它不修改算子源码、
不重新设计 `op_spec.py`，也不自行实现固件构建或烧录；构建交给 `hs-dev-build`，烧录交给
`hs-dev-flash`，本 Skill 在同一行、同一 receipt 返回后继续验收。
本 skill step0-3 负责模型、adaptor、Sample 和固件接线；workflow stage6 的 sample/adaptor/固件接线
必须完成后才能交给构建 Skill。

## 模式与固定流程

| 模式 | 起点 | 适用范围 |
|---|---|---|
| `prepare-build-flash-verify` | step0 | 顶层完整板端流程或用户要求从接线到精度 |
| `verify-prepared-firmware` | step4 | 用户明确已有身份可追踪的构建/烧录文件，只恢复证据并比较 |

按下表顺序逐行执行，不能选代表 case、跳过接线、合并不同 case 的库或复用旧轮次证据：

| Step | 动作 | 关键检查/阶段衔接 |
|---|---|---|
| 0 | 取得并核对用户提供的固件 SDK、chip、target 和运行环境 | `BOARD_SDK_GATE=PASS` |
| 0a | 预检本轮 framework 所需 Python 依赖 | `PY_DEPS_GATE=PASS` |
| 1 | 锁定 Host 生成的 `board_expected_matrix.json` 全部行 | 每行 Host 明确 PASS，测试点、模型/输入/GT/模式同轮且唯一 |
| 2 | 每行生成 Micro 工程并交叉编译 `libmicro_runtime.a`、`libnet.a` | 模型身份、dtype、Kernel 符号和 receipt 可追溯 |
| 3 | 每行安装 adaptor、生成 Sample、接入 CMake/Kconfig/target | `SAMPLE_PREP_GATE=PASS`、`BOARD_WIRING_GATE=PASS` |
| 4 | 委托 `hs-dev-build` clean build 并核对 fwpkg 内容 | `FIRMWARE_BUILD=PASS`、`FIRMWARE_CONTENT_GATE=PASS` |
| 5 | 委托 `hs-dev-flash`，采集本次烧录后的完整串口 Tensor | `FLASH_VERDICT=PASS`，monitor/端口/时间为本轮 |
| 6 | 用 `board_accuracy.py` 逐 Tensor 比较并生成矩阵报告 | `BOARD_MATRIX_GATE=PASS`、`ACCURACY_VERDICT=PASS` |

### 入口确认和自动推进

step0 之前只允许人工确认一次：`FIRMWARE_SDK_ROOT` 的绝对路径、目标 chip/board/target、环境和
本次是否执行板端范围。顶层 workflow 已完成这次 `EXECUTION_CONFIRM_GATE` 后，本 Skill 自动读取
矩阵、生成模型/代码、运行脚本、整理 handoff 和写结果，不在普通阶段询问“是否继续/是否上板”。
只有物理动作确实需要人在场（例如 `DEVICE_NOT_RESPONDING` 时按一次 RESET，或端口存在歧义时重新接线）
才按异常规则请求动作，并同时把当前行与剩余行状态保存到文件；不能把请求动作误当作重新确认整个流程。

缺少 SDK 路径、环境身份变化、依赖不可用或公共工具链失败时，保留已完成的 Host 状态，逐行写
`NOT_RUN`/`BLOCKED` 和恢复条件，不伪造 PASS、不缩小 expected 分母。WS63 细节只能在读取本目录
`chips/ws63/references/sdk-integration.md` 后执行；非 WS63 必须先提供对应 `<chip>-sdk-integration.md`
和确定性脚本。

## 矩阵与身份规则

唯一分母是同一轮 `hs-verify-op-host` 产生的 `board_expected_matrix.json`，完整 workflow 必须使用
Host `--target all`。固定顺序为 `framework → case_id → mode(fp32,int8)`；每行独立拥有模型、输入、
GT、`test_point`、Micro 库、Sample、fwpkg、flash JSON、monitor 和 `board_result.json`。`expected_count` 必须等于
cases 数量且每行 `host_status=PASS`；重复、缺失、跨 run/operator 或 Host FAIL 立即停止该行并记录。

同一行的模型库必须包含 `modelN.c`、`netN.c/ExecuteN()`、权威目标 Kernel 和真实 RISC-V 归档对象；
Sample 必须调用一次 `OH_AI_ModelPredict()` 并打印每个完整 Tensor 的 dtype、shape、元素数和 Data。
构建环境不同于设备 I/O 环境时，复制 fwpkg/库后按 receipt SHA-256 复核；不得用旧库、旧固件或手写
答案替代本次运行的文件。

## 交接边界

step3 完成后暂停当前矩阵行并把接线 receipt、target、模型库和 Sample 路径交给 workflow；workflow 在
同一进程导入脚本生成的环境文件后调用 `hs-dev-build`。step4 只接受新鲜 `_all.fwpkg` 及
`verify_firmware.py` 的 `FIRMWARE_CONTENT_GATE=PASS`，再交给 `hs-dev-flash`。flash 只认 stdout 最后
一行 JSON 的 `success=true`；`PORT_NOT_FOUND` 必须用新探测回执和有界 `--attempts/--interval` 重探，
`DEVICE_NOT_RESPONDING` 至多按规则做一次人工 RESET 重试，旧端口/旧 monitor 不能成为 PASS 证据。

进入对应阶段时读取详细接线、构建和返回字段：

1. [`references/workflow-gates.md`](references/workflow-gates.md)：职责边界、step0/0a、矩阵锁定和进度模板。
2. [`references/ws63-build-handoff.md`](references/ws63-build-handoff.md)：WS63 step2-step4 的 Micro、adaptor、Sample、SDK、构建接线和固件内容核对。
3. [`references/flash-serial-handoff.md`](references/flash-serial-handoff.md)：step5 的 flash 委托、串口交叉探测、重插重试和 monitor 证据。
4. [`references/board-accuracy-contract.md`](references/board-accuracy-contract.md)：step6 的 Tensor 解析、阈值、逐行结果和矩阵统计。
5. [`references/board-guardrails.md`](references/board-guardrails.md)：禁止事项、完成判据、失败措辞和资源所有权。

## 结果与完成语义

每行终态写入：

```text
<board-results>/<framework>/tc<case_id>/<mode>/board_result.json
```

至少包含 `run_id/operator/framework/case_id/mode/status/reason` 以及同一次运行的 model、input、GT、firmware、
flash、monitor、accuracy、serial probe 的绝对路径。所有行到达 `PASS|FAIL|NOT_RUN` 后运行：

```bash
python3 <skill_root>/scripts/board_matrix_report.py \
  --expected <same-run board_expected_matrix.json> \
  --results-dir <board-results> --output-dir <board-report-dir>
```

矩阵报告必须从 Host manifest 原样带出每行 `test_point`。只有
`expected=recorded=executed=pass`、`fail=not_run=0` 且 `BOARD_MATRIX_GATE=PASS`，同时每个 Tensor 达到
fp32 `cos >= 0.999` 或 INT8 `cos >= 0.99`，才可输出 `ACCURACY_VERDICT=PASS`。`executed=pass+fail`，
`NOT_RUN` 只能计入 recorded，不能计入 executed；烧录成功、启动日志、Sample 自报 PASS 或单个成功 case
都不等于全矩阵精度通过。

没有完整 shape/Data、同一次运行的 GT、flash JSON 或矩阵行时输出 `ACCURACY_VERDICT=NOT_RUN|FAIL` 并列出负责人。
未全矩阵通过时禁止使用“板测完成”“端到端通过”“验证全部通过”等完成语义；Host/固件构建通过但
板端未执行时，板端结果为 `ACCURACY_VERDICT=NOT_RUN`，workflow 收尾时整体记为
`OP_WORKFLOW=INCOMPLETE`。

## 资源索引

| 资源 | 用途 |
|---|---|
| [`references/workflow-gates.md`](references/workflow-gates.md) | 入口、授权、矩阵和进度 |
| [`references/ws63-build-handoff.md`](references/ws63-build-handoff.md) | WS63 模型库、Sample、SDK 接线和构建 handoff |
| [`references/flash-serial-handoff.md`](references/flash-serial-handoff.md) | flash/串口/端口重探和重试 |
| [`references/board-accuracy-contract.md`](references/board-accuracy-contract.md) | Tensor 精度和矩阵报告 |
| [`references/board-guardrails.md`](references/board-guardrails.md) | 禁止事项、完成判据和分流 |
| [`chips/ws63/references/sdk-integration.md`](chips/ws63/references/sdk-integration.md) | WS63 必读的具体 SDK 接线规范 |
| [`chips/ws63/references/device.md`](chips/ws63/references/device.md) | WS63 设备、端口和 I/O 环境事实 |
| [`chips/ws63/references/troubleshooting.md`](chips/ws63/references/troubleshooting.md) | WS63 接线/构建失败处理 |
| `scripts/probe_serial_ports.py` | 交叉探测并保存本轮端口回执 |
| `scripts/board_accuracy.py` | 唯一板端 Tensor 精度入口 |
| `scripts/board_matrix_report.py` | 逐行对账并生成汇总 |

reference 只从本入口直接链接；按当前阶段读取所需文件，避免一次加载全部板端实现细节。所有命令使用正斜杠和绝对路径。
