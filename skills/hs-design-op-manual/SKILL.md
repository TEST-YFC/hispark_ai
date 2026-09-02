---
name: hs-design-op-manual
description: >-
  Generate or synchronize the two human-readable MindSpore Lite Micro operator documents: a design
  document for specification, support limits, reuse decisions, scenarios, and call chains, and a
  verification document for test design, Host/firmware/flash/serial/board results, and evidence.
  Use when the user explicitly requests operator documentation, template analysis, or when
  hs-workflow-op-development routes an integrated-initial, integrated-final, or artifact-sync stage.
  Do not use this skill for source implementation, Host execution, firmware build, flashing, or board
  testing; generic implementation requests belong to hs-workflow-op-development. 中文触发包括“只生成算子文档”“算子设计文档”“算子规格文档”“验证文档”“模板分析”“同步文档”。
---

# 单算子设计文档生成器

本 Skill 只维护两份人读主文档，不实现源码、不运行构建或验证、不烧录。设计文档只写规格、支持范围、
七类能力复用裁决、关键场景和软件调用链；验证文档只写测试设计、用例矩阵、各阶段结果和证据索引。
机器 facts、日志、summary 和二进制产物是证据，不能替代主文档。

## 模式与边界

| 模式 | 触发场景 | 写入目标 |
|---|---|---|
| `standalone-generate` | 独立生成一对文档 | `<opdir>/docs/{op}-operator-design-doc.md` + `<opdir>/docs/{op}-operator-verify-doc.md` |
| `standalone-update` | 独立更新已有一对文档 | 同上 |
| `template-analysis` | 只分析模板 | 不写文件 |
| `integrated-initial` | `prepare` 后、源码前冻结初版 | facts + 一对 draft 文档 |
| `integrated-final` | 父流程终态同步 | facts + 一对终态文档 |
| `artifact-sync` | 从已有产物同步 | 一对文档；按 A/B/C/D 标注证据等级，D 不写文件 |

一次调用只能选择一个模式和一组固定目标。独立模式可在开始时确认代码根、`<opdir>`、算子名和框架；
产物集成模式只能使用父流程传入的绝对路径和冻结参数，不重新扫描仓库或查询外部规格。模式不匹配、
参数缺失、路径冲突或主源冲突时返回上游并 FAIL，不猜测补全。

## 固定工作流

按顺序执行下面七步，不能跳步、交换或把两个文档合并成一份：

| Step | 动作 | 必须满足的门禁 |
|---|---|---|
| 0 | 选择模式，核对授权参数和两个精确目标路径 | 范围、模式、目标明确 |
| 1 | 集成模式运行 `audit_manual_inputs.py` 并判定 A/B/C/D；独立模式完成已查证事实 | D 或核心冲突立即 FAIL |
| 2 | 集成模式从原始主源整份生成/刷新 `operator-manual-facts.json`；独立模式整理已查证事实 | schema、来源 hash、provenance 完整 |
| 3 | 分别生成设计候选和验证候选；终态从最新 facts 重建用例表和结果章节 | 两份文档职责分离，case 顺序及逐行测试点与 `op_spec.py` 一致 |
| 4 | 审核格式、来源、支持措辞、敏感信息和占位符 | 全部检查 PASS |
| 5 | 在 `<opdir>/docs/` 写临时候选，执行 facts/content/case audit | `OP_MANUAL_FACTS_SYNC=PASS`、`OP_MANUAL_CONTENT_SYNC=PASS`、`OP_MANUAL_CASE_SYNC=PASS` |
| 6 | 通过门禁后成对发布，重新读取并核对；任一步失败就回滚两份 | `OP_MANUAL_SYNC=PASS` 或明确 FAIL |

完整规则按阶段按需读取：

1. 先读 [`references/facts-contract.md`](references/facts-contract.md)，了解模式参数、唯一事实源、facts schema、输入审计和 A/B/C/D 分级。
2. 生成正文前读 [`references/document-rendering.md`](references/document-rendering.md)，并按需读两个文档模板。
3. 写入/发布前读 [`references/publication-transaction.md`](references/publication-transaction.md)，执行敏感信息检查、候选审计、成对事务发布和最终复核。

## 事实与自动化契约

产物集成模式只接受父流程冻结的：`code_root`、`opdir`、`op`/`Op`、`implementation_unit`、
`framework_scope`，以及 `integrated-final` 的 `terminal_state=completed|blocked|hard-stop`。父流程已经完成
环境和 SDK 的一次人工确认后，本 Skill 自动读取产物、生成 facts、渲染候选并运行审计，不再逐步询问用户。
独立模式仅在开始确认输入/目标路径；确认后生成和更新由 agent 自动完成。

facts 的四个主源固定为：

- 设计规格和软件设计：`<opdir>/docs/spec.md`、`implementation-contract.md`；
- 场景和能力：`<opdir>/scripts/capability_checklist.json`；
- 验证用例：`<opdir>/scripts/op_spec.py`；
- 结果：本轮可信 `verify_summary.txt`、板端矩阵及其证据。

只写已公开、已核对或已冻结的事实。缺少转换入口写“不支持转换”，缺少类型写“不支持该类型”，
属性/shape/layout/target 不支持写“不支持该规格”；不得把未执行写成 PASS、不得从聚合路径猜逐 case
结论、不得写“待确认”或内部路径。`integrated-initial` 只能表示编码前计划冻结，不能表示源码、构建或验证完成。

## 文档职责与输出

设计文档必须保留三个一级章节：算子概述、框架算子规格、MindSpore Lite Micro 软件设计，并覆盖
Schema、Parser、Populate/Parameter、Infer、Kernel、OpCoder、Quantizer 七类能力及真实调用链。
验证文档必须保留测试覆盖原则、带“测试点”列的逐 case 用例表、Host/固件/烧录/串口/板端状态和证据索引；未执行阶段写
`NOT_RUN` 及原因。不得在设计文档混入运行或板测结果，也不得在验证文档重复完整软件设计。

所有写入模式都输出同一对绝对目标文件；`template-analysis` 和 A/B/C/D 的 D 级只输出分析，不伪造文件。
发布最后一行使用：

```text
OP_MANUAL_SYNC=PASS mode=<mode> publication=<final|record|none> design_path=<absolute-path|NONE> verify_path=<absolute-path|NONE>
OP_MANUAL_SYNC=FAIL mode=<mode> publication=none design_path=NONE verify_path=NONE
```

若 facts、content 或 case 任一审计失败，丢弃候选且不覆盖已有文档。终态和证据等级不能被文档反向改写。

## 资源索引

| 资源 | 何时读取 |
|---|---|
| [`references/facts-contract.md`](references/facts-contract.md) | step0-step2、输入审计、facts 和分级 |
| [`references/document-rendering.md`](references/document-rendering.md) | step3、章节和逐 case 渲染 |
| [`references/publication-transaction.md`](references/publication-transaction.md) | step4-step6、公开边界、回滚和自检 |
| [`references/operator-design-doc-template.md`](references/operator-design-doc-template.md) | 设计文档候选 |
| [`references/operator-verify-doc-template.md`](references/operator-verify-doc-template.md) | 验证文档候选 |
| `scripts/audit_manual_inputs.py` | 集成模式输入、facts 和候选的机械审计 |

reference 只从本入口直接链接；引用文件内部的规则不构成另一层必读入口。所有路径在实际命令中使用正斜杠和绝对路径。
