# {Op} 算子开发与验证记录

> 状态：{PLANNED | INCOMPLETE | FAIL | PASS | HOST_ONLY_PASS}
>
> 文件位置：`<opdir>/docs/operator-development-report-{op}.md`。这是一份 implementation unit 的唯一人读主文档。阶段证据仍保存在 JSON、日志、模型、库和
> 固件文件中；本文件只写结论、关键路径和证据链接，不复制大段日志。

## 0. 状态与结论

| 项目 | 内容 |
|---|---|
| 算子/implementation unit | {填写} |
| 框架与 source entry | {ONNX/TFLite 及节点名} |
| 代码根与版本 | {路径、commit 或源码指纹} |
| MindSpore Lite 工具包 | {路径、版本、哈希} |
| 芯片/SDK/target | {WS63 等；仅要求板测时填写} |
| 当前结论 | {用人话说明做到哪一步、能否用于目标设备} |

| 阶段 | 状态 | 证据 |
|---|---|---|
| 设计与计划 | {PASS/FAIL} | {spec、contract、checklist} |
| 文档先于代码 | {PASS/FAIL} | {本文件初版、facts、audit} |
| 源码实现与审查 | {PASS/FAIL/NOT_RUN} | {代码路径、code-review} |
| MindSpore Lite 构建 | {PASS/FAIL/NOT_RUN} | {MSLITE_PKG、build log} |
| Host 全量验证 | {PASS/FAIL/NOT_RUN} | {verify_summary} |
| 固件构建矩阵 | {PASS/FAIL/NOT_RUN} | {firmware report} |
| 真实板烧录与串口 | {PASS/FAIL/NOT_RUN} | {flash JSON、monitor} |
| 板端精度矩阵 | {PASS/FAIL/NOT_RUN} | {board summary} |

## 1. 算子概述

### 1.1 功能和数学定义

{用白话说明功能；公式只来自已核对的规格。}

### 1.2 最小示例

{输入 shape、dtype、属性和输出的简短示例。}

## 2. MindSpore Lite Micro 功能规格

### 2.1 框架规格

| 框架/source entry | opset/builtin | 属性 | 输入/输出 | dtype/shape | 支持范围与限制 |
|---|---|---|---|---|---|
| {填写} | {填写} | {填写} | {填写} | {填写} | {填写} |

### 2.2 已有能力与复用裁决

| 能力 | 复用/修复/新建 | 主要文件或注册点 | 依据与限制 |
|---|---|---|---|
| Schema | {填写} | {填写} | {填写} |
| Parser | {填写} | {填写} | {填写} |
| Populate/Parameter | {填写} | {填写} | {填写} |
| Infer | {填写} | {填写} | {填写} |
| Kernel | {填写} | {填写} | {填写} |
| OpCoder | {填写} | {填写} | {填写} |
| Quantizer | {填写} | {填写} | {填写} |

{说明 Primitive、注册键、图优化/常量折叠/fusion/rewrite，以及不支持或延期范围。}

## 3. 关键场景分析

### 3.1 关键使用场景

| 使用场景 | 什么时候会遇到 | 已覆盖行为与限制 | 对应用例 |
|---|---|---|---|
| {填写} | {填写} | {填写} | TC-001 |

### 3.2 完整调用链

{本节标题和“转换/生成期”定位固定，但正文不是固定文案。必须根据当前算子的真实源码、注册关系和复用裁决，
写出具体 Parser、Primitive/Schema、Parameter、Infer、图优化/量化、OpCoder、生成函数和静态库；
不得原样复制下面的结构骨架，不适用的环节写 `N/A` 并说明原因。}

```text
{实际源模型节点} → {实际 Parser::Parse} → {实际 Primitive/Schema}
→ {实际 Populate/Parameter} → {实际 Infer} → {实际图优化/量化或 N/A}
→ {实际 OpCoder} → converter_lite 生成 {ExecuteN()/net*.c 等实际产物} → {实际静态库}
```

### 3.3 板端运行链

{本节标题和“运行期”定位固定，但正文必须按当前 Sample、模型入口、ExecuteN()、Kernel、串口协议和
精度比较代码重写。没有上板目标或没有可信板端证据时写 `N/A` 或 `NOT_RUN` 及原因，不得臆造函数。}

```text
{实际应用/Sample入口} → {实际模型API，如 OH_AI_ModelPredict}
→ {实际 ExecuteN()/模型生成入口} → {实际 Kernel函数}
→ 输出 Tensor → {实际串口采集与精度比较路径}
```

{必须结合当前算子说明七类能力分别在哪个阶段使用。固定结论是：七类能力不是每次推理按顺序执行；
Parser/Populate/Infer/OpCoder主要在转换或生成期，Kernel在运行期执行。}

## 4. 测试设计

### 4.1 测试覆盖原则

{输入规模/shape、属性、边界、折叠或重写、量化/原生整数、GT和判定方法。}

### 4.2 用例总表

| 用例编号 | 框架/source entry | 模型 dtype | 已覆盖运行通路 | input_shape | 输入数据特征（value_domain） | 算子属性 | 预期输出 |
|---|---|---|---|---|---|---|---|
| TC-001 | {填写} | {填写} | {填写} | {填写} | {填写} | {填写} | {填写} |

### 4.3 结果汇总（终态回填）

| 阶段 | 结果 | 数量 | 原因/证据 |
|---|---|---|---|
| Host 全量验证 | {PASS/FAIL/NOT_RUN} | {passed/expected} | {路径} |
| 固件构建矩阵 | {PASS/FAIL/NOT_RUN} | {built/expected} | {路径} |
| 真实板烧录 | {PASS/FAIL/NOT_RUN} | {executed/expected} | {路径；未执行原因} |
| 串口 Tensor 与板端精度 | {PASS/FAIL/NOT_RUN} | {pass/expected} | {路径；未执行原因} |

{最终结论必须区分 Host、固件构建和真实板测；有 NOT_RUN 时不能写无范围“验证通过”。}

### 4.4 每个用例的阶段状态

| 用例编号 | Host | 固件构建 | 真实板烧录 | 板端精度 |
|---|---|---|---|---|
| TC-001 | {PASS/...} | {PASS/...} | {PASS/...} | {PASS/...} |

### 4.5 证据索引

{列出 source-freeze、facts、op_spec、Host summary、board_expected_matrix、逐case结果、
日志、库、fwpkg 和哈希的路径。}
