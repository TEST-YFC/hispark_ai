# Stage1 规划与文档先行细则

## 目录

- [固定顺序](#stage1实现计划和初版文档先行)
- [源码冻结和回流](#源码冻结和回流)

> 进入 Stage1 后按入口表中的顺序读取。这里保留 prepare、integrated-initial、pre-source 的完整门禁关系。

## stage1：实现计划和初版文档先行

仅当`EXECUTION_CONFIRM_GATE=PASS`时进入本阶段；`PENDING`或缺少记录都必须停在Stage0。

进入本阶段先将 `stage1.plan` 标为 `RUNNING`，并在计划、初版文档和
`PRE_SOURCE_GATE` 各自完成后立即分别落盘 `PASS`；任一门禁失败要写入首个错误和证据路径，
不得只在对话中口头记账。

本阶段固定按下面顺序执行，不能把三个动作合并或调换：

1. 生成本轮唯一`OP_PLAN_RUN_ID`并调用`hs-dev-op-implement mode=prepare`。它先运行
   `gate_artifacts.py --stage source-freeze --plan-run-id <ID>`生成绑定算子、框架范围和code root的
   `source-freeze.json`，再执行step0-step3，生成并冻结
   `spec.md`、`decision.md`、`link-analysis.md`、`existing-capability-review.md`、
   `implementation-contract.md`、`capability_checklist.json`和计划版`op_spec.py`；运行
   `validate_op_spec.py`及带`--code-root`的`gate_artifacts.py --stage prepare`。prepare期间禁止修改Schema、
   Parser、Populate、Infer、Kernel、OpCoder、Quantizer、注册或构建接线源码。只有
   `OP_SPEC_GATE=PASS`和每个framework的`OP_PLAN_GATE=PASS`才继续。
2. 顶层workflow调用`hs-design-op-manual mode=integrated-initial`。文档Skill只消费第1步
   已冻结的四个主源，不负责扫描或生成实现合同，输出
   `operator-manual-facts.json`、`{op}-operator-design-doc.md`和`{op}-operator-verify-doc.md`。只有
   `OP_MANUAL_SYNC=PASS mode=integrated-initial publication=record`才继续。
3. 对每个framework运行带`--code-root`的`gate_artifacts.py --stage pre-source`，机械复核
   `source-freeze.json`中的源码指纹、计划版`op_spec.py`、facts、两份文档以及facts记录的
   `spec/implementation-contract/capability-checklist/op_spec`哈希，并重新执行facts/content/case
   三项文档audit。
   只有全部输出`PRE_SOURCE_GATE=PASS`才能进入stage2。

## 源码冻结和回流

`source-freeze.json`记录prepare开始前的Git可见源码指纹，prepare和pre-source使用同一
`OP_PLAN_RUN_ID`机械复核指纹不变；`<opdir>`中的规划和草稿文件变化不算算子源码写入。
任何`code_root`内的①-⑦源码、注册或MindSpore Lite构建接线在`PRE_SOURCE_GATE=PASS`前
发生变化，都使本轮stage1失败，必须查明来源并重新执行prepare，不能用后补文档掩盖顺序错误。

同一`OP_PLAN_RUN_ID`禁止覆盖freeze receipt。上一轮stage1已结构化终止并明确开始新规划轮次时，
才可生成新ID并显式rotate；旧receipt必须归档，不得静默重置基线。固件SDK不属于本门禁范围，
其写入授权、接线receipt和新鲜度由stage6单独门控。

实现过程中若规格、合同、能力清单或计划用例需要变化，停止源码修改并回到stage1完整重跑
prepare→integrated-initial→pre-source；不能先改代码再更新草稿。
