---
name: hs-verify-op-host
description: >-
  Design, run, and debug PC/WSL Host precision tests for an existing MindSpore Lite Micro operator.
  Use when the user explicitly names hs-verify-op-host, asks only to write operator tests or verify
  Host accuracy, or hs-workflow-op-development routes a test-spec/harness defect here. It owns the
  single op_spec.py, deterministic ONNX/TFLite cases, reference outputs, fixed harness, capability
  coverage, x86 execution of x86/RISC-V code-generation paths, and VERDICT reporting. Do not use it
  for operator implementation, firmware build, flashing, or real-board verification; combined or
  generic operator requests belong to hs-workflow-op-development. 中文触发包括“Host 验证”“电脑端精度”“只写算子测试”；
  固件、烧录或真板请求应使用 workflow/board Skill。
---

# 算子 Host 正确性验证

本 Skill 只负责 PC/WSL 上的 Host 测试设计和精度验证。每个算子只写一个 `<opdir>/scripts/op_spec.py`；
模型生成、转换、编译、推理、余弦计算、Excel 和 summary 都由仓内固定 harness 完成。ONNX 与 TFLite
是两条独立路径，各自维护用例和结果；`riscv_*` 目标仍在 Host 执行，不代表真实板运行。

## 固定工作流

先创建下面的 todo。每一步完成后把证据保存到状态目录，再进入下一步：

| Step | 动作 | 通过证据 |
|---|---|---|
| 0 | 准备工具包、运行环境和算子项目目录 | `converter_lite` 可执行；`op_spec.py` 不在源码/构建树 |
| 1 | standalone 编写或 workflow 只读对账 `op_spec.py` | `OP_NAME`、激活框架 cases、逐 case `test_point`、builder、`make_inputs()` 完整；检查通过 |
| 2 | 调用唯一 `run_all_cases.py` harness | 每条用例内部 step1-step5 串行完成 |
| 3 | 读取本轮结果 | `VERDICT` 后紧随 `HARNESS_EXIT`，summary/Excel/日志同一 `RUN_ID` |
| 4 | 根据证据排查并报告结果 | 非零退出如实 FAIL；只有 harness 全绿才 PASS |

进入对应阶段时读取详细说明：

1. [`references/workflow-gates.md`](references/workflow-gates.md)：用户可见 todo、流程地图、harness 内部步骤和 workflow 的 pre-verify 检查。
2. [`references/host-guardrails.md`](references/host-guardrails.md)：不可变 harness、余弦/INT8 防伪、目录和依赖红线及前置检查。
3. [`references/host-contract.md`](references/host-contract.md)：`op_spec.py`、能力清单、输入/输出和两框架用例设计的完整规则。
4. [`references/run-and-results.md`](references/run-and-results.md)：运行命令、长任务等待、结果文件和报告格式。
5. [`references/failure-triage.md`](references/failure-triage.md)：converter/工具链/实现失败分流、处理方式和范围底线。

## 调用边界与自动推进

完整 workflow 传入的 `<opdir>`、框架范围、实现约束、能力清单和计划 `op_spec.py` 已在上游确定；本
Skill 只能只读对账，发现 case、GT、覆盖映射或源码指纹变化就回到 workflow stage1，不能在 Host 阶段
悄悄改 spec 继续跑。独立 Host 请求在开始时确认一次代码/工具包和目标目录；收到确认后，spec 生成、
依赖修复、harness 运行、结果读取和失败处理由 agent 自动完成，不逐步询问用户。轻量 Python 依赖可在
同一解释器的虚拟环境或用户范围自动修复；超出安全边界才报告阻塞。

本 Skill 不实现算子、不修改 bundled harness、不构建固件、不烧录、不读取真实板串口。任何需要这些动作
的请求都返回 `hs-workflow-op-development` 或对应专项 Skill。

## 唯一输入和自动检查

`op_spec.py` 是本 Skill 唯一允许为具体算子新建或编辑的文件。它必须声明本算子和本次范围内真实存在的
ONNX/TFLite source entry，提供相应 builder、确定性 `make_inputs()`、两套独立 cases 和精确目标身份；
不得以等价 builtin 顶替、按形状静默切换算子、手填 GT 或余弦值。完整 workflow 启动前依次通过：

```bash
python3 <hs-dev-op-implement>/scripts/gate_artifacts.py \
  --opdir <absolute-opdir> --op <Op> --stage pre-verify --framework <framework>
python3 <hs-verify-op-host>/scripts/validate_op_spec.py <absolute-opdir>
```

每个激活 framework 都必须得到 `ARTIFACT_GATE=PASS` 且 validator 退出 0。harness 自己还会检查目标节点/
builtin 身份、动态输入与 initializer 数量、能力 `covered_by` 引用、常量折叠/节点重写双路径和 INT8 真
实性；不得删除 FAIL case、缩小分母、降低阈值或改 GT 换绿。

## 运行和结论规则

使用绝对 spec 路径调用固定入口；不要手敲 converter、cmake 或 benchmark，也不要复制/修改 bundled 脚本：

```bash
python3 <hs-verify-op-host>/scripts/run_all_cases.py \
  --spec <absolute-opdir>/scripts/op_spec.py --framework <onnx|tflite|all> \
  --target <all|x86|riscv> --run-id <unique-run-id>
```

长任务只用 `scripts/wait_verify.sh` 有界等待。每条内部路径必须先生成确定性模型/输入和参考输出，再
转换、编译、写入 bin、运行 benchmark 打印完整输出张量，最后由 Python `cosine_similarity()` 统一比较；
fp32 阈值为 `0.999`，INT8 为 `0.99`。全量化 INT8 还必须命中声明的 int8 kernel；原生整数路径单独报告。

只认本轮 harness 的最后一组 `VERDICT`、紧随其后的 `HARNESS_EXIT=N`、`verify_summary.txt`、对应 Excel
和逐路径 stderr。`HARNESS_EXIT!=0` 就是 FAIL；不能凭日志片段、启动成功、聚合 `paths=[...]` 或记忆宣布
通过。只有全部激活 framework 的全部计划 case 在全部激活 path 上完成且 PASS，才能输出
`HOST_VERIFY_GATE=PASS`；跑通一条或部分用例只能报告局部结果。结果缺失、RUN_ID 不一致、旧日志或
任一用例失败都必须保留原文并交给对应负责人。Excel 和逐 case 摘要必须显示 `test_point`，明确每条用例验证什么。

## 输出与交接

结束时先列每个 framework/case/path 的测试点和状态，再给机器可读摘要：

```text
HOST_VERIFY_GATE=<PASS|FAIL>
RUN_ID=<本轮唯一ID>
OP_SPEC=<absolute op_spec.py>
VERDICT=<harness 原文>
HARNESS_EXIT=<N>
VERIFY_SUMMARY=<absolute path>
ONNX_EXCEL=<absolute path|NONE>
TFLITE_EXCEL=<absolute path|NONE>
next_owner=<hs-workflow-op-development|implementation|toolchain>
```

`HOST_VERIFY_GATE=PASS` 只表示本轮 Host 范围的全部激活 cases 和路径已由 harness 记录，不表示源码实现、
固件、烧录或板端精度通过。Host PASS 后交给 workflow 生成 `board_expected_matrix.json`；不能在此自行
扩大或缩小板端分母。

## 资源索引

| 资源 | 用途 |
|---|---|
| `scripts/run_all_cases.py` | 唯一不可变 harness 入口 |
| `scripts/validate_op_spec.py` | 长任务前的 spec 自动检查 |
| `scripts/wait_verify.sh` | 后台任务的有界等待 |
| `scripts/judge.sh` | 单 case 诊断；不形成最终结论 |
| [`references/workflow-gates.md`](references/workflow-gates.md) | step0/1 和 workflow 对账 |
| [`references/host-guardrails.md`](references/host-guardrails.md) | 禁止事项、依赖和目录边界 |
| [`references/host-contract.md`](references/host-contract.md) | spec、能力和用例完整规则 |
| [`references/run-and-results.md`](references/run-and-results.md) | 执行、等待、结果读取 |
| [`references/failure-triage.md`](references/failure-triage.md) | 失败排查与处理 |

所有 reference 只从本入口直接链接；按当前阶段读取所需文件，避免把完整 harness 细节一次性加载。
