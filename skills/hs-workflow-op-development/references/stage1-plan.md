# Stage1 规划与文档先行细则

> 本文件对应 Stage1，任务 ID 使用 `stage1.*`。

## 目录

- [固定顺序](#stage1实现计划和初版文档先行)
- [源码冻结和重新规划](#源码冻结和重新规划)

> 进入 Stage1 后按入口表中的顺序读取。这里保留 prepare、integrated-initial、pre-source 的完整门禁关系。

## Stage1：实现计划和初版文档先行

仅当`EXECUTION_CONFIRM_GATE=PASS`时进入本阶段；`PENDING`或缺少记录都必须停在Stage0。

进入本阶段后，先将 `stage1.plan` 标为 `RUNNING`。计划、初版文档和 `PRE_SOURCE_GATE`
各自完成后，立即分别落盘 `PASS`。任一门禁失败时，写入首个错误和证据路径，不能只在对话中记录。

本阶段固定按下面顺序执行，不能把三个动作合并或调换：

1. 生成本轮唯一的`OP_PLAN_RUN_ID`，并调用`hs-dev-op-implement mode=prepare`。先运行
   `gate_artifacts.py --stage source-freeze --plan-run-id <ID>`，生成绑定算子、框架范围和 code root 的
   `source-freeze.json`；再执行 step0-step3，生成并冻结 `spec.md`、`decision.md`、`link-analysis.md`、
   `existing-capability-review.md`、实现约定文件`implementation-contract.md`、
   `capability_checklist.json`和计划版`op_spec.py`。每条 case 的 `test_point`必须明确说明该用例验证的行为、
   边界或缺陷类型。然后运行 `validate_op_spec.py`和带`--code-root`的`gate_artifacts.py --stage prepare`。
   prepare 期间禁止修改 Schema、Parser、Populate、Infer、Kernel、OpCoder、Quantizer、注册或构建接线源码。
   得到`OP_SPEC_GATE=PASS`和每个 framework 的`OP_PLAN_GATE=PASS`后，才能继续。
2. 顶层 workflow 调用`hs-design-op-manual mode=integrated-initial`。文档 Skill 只消费第 1 步确定的四个主源，
   不负责扫描或生成实现约定。输出包括`operator-manual-facts.json`、`{op}-operator-design-doc.md`和
   `{op}-operator-verify-doc.md`。得到`OP_MANUAL_SYNC=PASS mode=integrated-initial publication=record`后，才能继续。
3. 对每个 framework 运行带`--code-root`的`gate_artifacts.py --stage pre-source`。该命令复核
   `source-freeze.json`中的源码指纹、计划版`op_spec.py`、facts、两份文档，以及 facts 记录的四份主源文件哈希：
   `spec.md`、实现约定文件、能力清单和计划版`op_spec.py`。同时重新执行 facts/content/case 三项文档 audit。
   审计脚本位置通过 `--manual-audit-script` 传入；完整命令见 `hs-dev-op-implement` 内的
   `references/implementation-detail.md` 的 pre-source 小节。全部输出`PRE_SOURCE_GATE=PASS`后，才能进入 Stage2。

## 源码冻结和重新规划

`source-freeze.json` 记录 prepare 开始前 Git 可见的源码指纹。prepare 和 pre-source 使用同一
`OP_PLAN_RUN_ID`，复核指纹是否保持不变；`<opdir>` 中的规划和草稿文件变化不算算子源码写入。
如果 `code_root` 内的①-⑦源码、注册或 MindSpore Lite 构建接线在 `PRE_SOURCE_GATE=PASS` 前发生变化，
本轮 Stage1 失败。查明来源后重新执行 prepare，不能用补写文档掩盖顺序错误。

同一 `OP_PLAN_RUN_ID` 对应的 freeze receipt 不得覆盖。只有上一轮 Stage1 已结束，并且明确开始新的规划轮次时，
才能生成新 ID。归档原 receipt，保留原基线。固件 SDK 不属于本门禁范围；
其写入授权、接线 receipt 和新鲜度由 Stage5 单独控制。

实现过程中若规格、实现约定、能力清单或计划用例需要变化，停止源码修改并回到 Stage1，
按入口规定的固定顺序完整重跑。
