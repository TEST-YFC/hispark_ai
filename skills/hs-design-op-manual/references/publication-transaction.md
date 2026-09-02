# 公开边界与事务发布

目录：

- [敏感信息与公开边界](#敏感信息与公开边界)
- [执行顺序](#执行顺序)
- [输出决策](#输出决策)
- [自检与最终复核](#自检与最终复核)
- [变量与参考](#变量与参考)

以下内容是 `hs-design-op-manual/SKILL.md` 的按需细节，发布和回滚步骤保持不变。

## 敏感信息与公开边界

违反任一项即返工：

- 禁止写需求号、任务号、缺陷号、工号、员工号、审批/评审单号、内部编号，或 `AR/MR/CR` 等内部流转编号。
- 禁止写 `REQ-123`、`TASK-123`、`BUG-123`、`JIRA-123`、`MS-1234`、`PRJ-1234`、`AR-123`、`MR-123`、`CR-123`、带标签的六位以上数字串，以及此类占位符。
- 禁止写“Bug号”“问题单号”“xxx编号”“请补编号”“待补编号”“内部单号”或“补 AR/MR/CR 单号”等字段/占位描述。
- 禁止私有系统链接和含 `ar_id=`、`mr_id=`、`cr_id=`、`taskId=`、`issueId=` 的参数。
- 设计文档为说明七类能力和真实调用链，可以写仓库相对源码路径、PrimitiveType、公开注册符号、
  Kernel/OpCoder 分支和量化设计事实；验证文档不重复这些完整设计。
- 禁止写本机绝对路径、个人工作区、临时目录、账号/密钥、私有系统链接、内部缺陷动作或与算子
  设计无关的内部实现细节。
- 公开测试用例号 `TC-*` 是必要文档标识，不属于敏感编号，必须按 op_spec 保留。
- 全文不得出现“待确认”。证据不足时停止并返回上游，而不是把不确定性发布出去。

支持状态固定用语：

| 情况 | 写法 |
|---|---|
| source entry/parser 无转换入口 | `不支持转换` |
| 模型 dtype/目标类型无支持记录 | `不支持该类型` |
| 属性、shape、layout、方向、variant 或验证 target 不支持 | `不支持该规格` |

## 执行顺序

| Step | 动作 | 门控 |
|---|---|---|
| step0 | 选择模式；独立模式一次性核对授权参数和两个精确目标路径，产物集成模式校验父参数和绝对路径 | 模式、范围、设计/验证目标明确 |
| step1 | 产物集成模式运行输入 audit；`artifact-sync` 按 A/B/C/D 分级 | D 或核心冲突立即 FAIL |
| step2 | 产物集成模式从原始主源创建/整份刷新 `operator-manual-facts.json`；独立模式整理已查证事实但不生成 facts 文件 | 集成模式 facts schema 完整；所有模式遇到缺失和冲突都停止，不发明 |
| step3 | 产物集成模式从 facts、独立模式从已查证事实，在内存中分别生成设计和验证候选；终态重建验证用例表和结果章节 | 两份文档职责完整；验证 case 顺序和逐字段值一一对应 |
| step4 | 对候选做格式、来源、支持措辞、敏感信息和 placeholder 自检 | 全部 PASS 才能进入发布门控 |
| step5 | 将两份候选分别写入 `<opdir>/docs/` 的临时文件；产物集成模式对 facts 和两份候选运行完整 audit，独立模式运行格式、事实来源和职责边界自检 | 集成模式三项 audit 均 PASS；独立模式自检全部 PASS |
| step6 | 对应门禁 PASS 后执行带备份回滚的成对发布；重新读取两份目标并打印 `OP_MANUAL_SYNC` | 两份目标同时更新并复核 PASS，或两份都恢复发布前状态并 FAIL |

现有两份文档在发布门控通过前不得直接修改。候选优先保留在内存；执行发布门控时，才在目标文档
同目录创建可精确识别的临时候选。下面命令用于
产物集成模式：

```bash
design_candidate="$(mktemp "${design_path}.candidate.XXXXXX")"
verify_candidate="$(mktemp "${verify_path}.candidate.XXXXXX")"
# 将内存候选分别写入两个候选文件，不要直接写正式目标
python3 <manual_skill_root>/scripts/audit_manual_inputs.py \
  --opdir <absolute_opdir> \
  --facts <absolute_opdir>/docs/operator-manual-facts.json \
  --design "$design_candidate" \
  --verify "$verify_candidate" \
  --publication <draft|evidence-draft|final>
```

只有 `OP_MANUAL_FACTS_SYNC=PASS`、`OP_MANUAL_CONTENT_SYNC=PASS` 和 `OP_MANUAL_CASE_SYNC=PASS`
同时成立，才成对发布两份候选。发布必须按以下事务式顺序执行：

1. 在 `<opdir>/docs/` 中分别为当前设计、验证目标创建可精确识别的临时备份；目标原先不存在时
   记录 `ABSENT`，不得伪造空备份。
2. 依次以同目录 rename/move 替换设计目标和验证目标；单个替换可以利用同一文件系统的原子
   rename，但不得声称两个替换天然构成一个原子事务。
3. 任一替换失败，立即从备份恢复已经替换的目标；发布前为 `ABSENT` 的目标必须删除。重新读取
   两个目标，确认都回到发布前状态，然后输出 `OP_MANUAL_SYNC=FAIL`。
4. 两个替换都成功后，重新读取两份目标并复跑内容/职责边界检查；全部 PASS 后才能删除备份并
   输出 `OP_MANUAL_SYNC=PASS`。复核失败也执行步骤 3 的回滚。

门禁 FAIL 或命令异常时丢弃两个候选，不改正式目标。候选和备份都不是持久输出，成功或回滚后
不得残留。不得为取得 PASS 修改 op_spec、capability 或 summary。独立模式不执行 facts audit，
但也必须先完成 step4 自检，再按同一成对发布与回滚规则更新 `<opdir>/docs/` 中的两个目标。

Stage0 尚未完成执行确认时，父 workflow 的 `stage5.final_docs` 只记录阻断原因、恢复条件和状态证据，
不调用本 Skill，也不生成或覆盖正式文档；本节 `integrated-final` 的 `record` 发布规则仅适用于
已经完成 Stage0 确认的运行。

产物集成模式的正式发布必须同时满足：父终态允许发布、产物等级允许发布、facts `provenance=production`、`production_eligible=true`，以及 facts/content/case 三项同步 PASS。

## 输出决策

产物集成模式的 `{op}` 使用父流程冻结的小写发布名。每个算子固定生成两份文档：
`{op}-operator-design-doc.md` 和 `{op}-operator-verify-doc.md`。两份文件名都包含算子名，保证文档复制或脱离 `opdir` 后仍可识别；模板源文件按设计/验证各自维护，不按算子复制或改名。

| 模式/状态 | publication | 目标 |
|---|---|---|
| `standalone-generate` / `standalone-update` | `final` | `<opdir>/docs/{op}-operator-design-doc.md` + `<opdir>/docs/{op}-operator-verify-doc.md` |
| `template-analysis` | `none` | `NONE` |
| `integrated-initial` | `record` | `<opdir>/docs/{op}-operator-design-doc.md` + `<opdir>/docs/{op}-operator-verify-doc.md` |
| `integrated-final terminal_state=completed` | `record` | 同上，同时回填验证结果 |
| `integrated-final terminal_state=blocked\|hard-stop` | `record` | 同上，验证文档记录 NOT_RUN/FAIL 原因 |
| `artifact-sync` A 且 facts 内容完整 | `record` | 同上 |
| `artifact-sync` A 但 facts 内容不完整 | `record` | 同上并标注证据不足 |
| `artifact-sync` B/C | `record` | 同上并保留 FAIL/NOT_RUN |
| `artifact-sync` D | `none` | `NONE` |

一次调用不得同时刷新 draft 和 final；除 mandatory facts 中间产物外，必须成对提升设计文档和验证文档。完成或失败时，最后一行使用：

说明：`record` 是工作流对“两份主文档”的发布标识；底层 `audit_manual_inputs.py` 仍使用
`--publication=draft|final` 表示审计严格程度。

```text
OP_MANUAL_SYNC=PASS mode=<mode> publication=<final|record|none> design_path=<absolute-path|NONE> verify_path=<absolute-path|NONE>
OP_MANUAL_SYNC=FAIL mode=<mode> publication=none design_path=NONE verify_path=NONE
```

失败详情在终态行之前简要列出并返回父流程。`integrated-initial`失败会阻塞进入编码；`integrated-final`失败会阻塞完成声明。两份文档只能由冻结facts和同轮终态证据渲染，不能成为另一套手工维护的事实源。

## 自检与最终复核

候选提升前逐项检查：

- [ ] 模式、授权和设计/验证输出路径与决策表一致。
- [ ] 产物集成模式已从本次最新原始源刷新 `operator-manual-facts.json`；source path/hash、quote、case 顺序和 provenance 均正确。
- [ ] 设计文档和验证文档各只有规定的三个一级编号章节；独立模式使用已查证事实构建，产物集成模式每章来自规定主源。
- [ ] capability 多于 7 项时，第 3 章已归并为 3～7 个读者场景；每个 capability 恰好出现一次，group 用例号是成员 `covered_by` 的准确并集。
- [ ] 验证文档 `1.1 测试覆盖原则` 的四个问题和答案来自 `coverage_principles`，使用用户语言解释覆盖范围，没有流程术语堆叠。
- [ ] 产物集成模式没有仓库重扫、外部查询、build、verify 或 board 重跑。
- [ ] 现有设计/验证文档没有覆盖冻结事实；终态的验证文档用例表和结果章节已经整表重建并回填结果。
- [ ] formula/full name/category 未被发明；缺公式时已省略。
- [ ] 不支持项使用固定措辞，C 级失败 variant/target/path 未写成支持。
- [ ] 模型 dtype、已覆盖运行通路、value_domain/输入数据特征各自保留且没有混淆；机器验证标识只保留在 facts，公开设计文档已转换为实际运行含义。
- [ ] 文档标题和正文定位为算子设计文档；全文没有出现内部验证任务名。
- [ ] 产物集成模式中 op_spec 每个 case 恰好一行，原始 `TC-*` ID 未重排；每行“测试点”与 `test_point` 一致；每个 `covered_by` 都存在。
- [ ] 全文没有本机绝对路径、内部流转信息、私有链接或“待确认”；设计所需的仓库相对路径和公开符号已保留。
- [ ] facts/content/case 任一 audit 尚未通过时，既有两份文档仍未被覆盖；失败临时候选会被丢弃。
- [ ] 成对发布任一步失败时，两份目标都恢复发布前状态；两份目标版本一致，且没有候选或备份残留。

提升后重新读取目标并确认：

1. 写入模式的设计文档和验证文档均已写入决策表指定路径；零写入模式没有文档，且没有残留临时候选。
2. 两份文档各自的三个一级编号章节、表头和支持措辞完整，已移除 case 不残留，新增 case 不遗漏。
3. 产物集成模式的输出得到 `OP_MANUAL_FACTS_SYNC=PASS`、`OP_MANUAL_CONTENT_SYNC=PASS` 和 `OP_MANUAL_CASE_SYNC=PASS`；否则不得更新任一文档或报告同步成功。
4. terminal_state 和产物等级没有被文档内容反向改写。

## 变量与参考

| 变量 | 含义 |
|---|---|
| `<manual_skill_root>` | `hs-design-op-manual` skill 的绝对目录 |
| `<code_root>` | MindSpore Lite 代码根绝对路径 |
| `<opdir>` | 单个 implementation unit 的绝对工作目录 |
| `design_path` / `verify_path` | 按输出决策表解析出的两份持久文档目标绝对路径 |
| `{op}` / `{Op}` | 小写发布文件名 / 公开算子或 unit 名 |
| `framework_scope` | 父流程冻结的 source entry / 框架集合 |
| `terminal_state` | `integrated-final` 的 `completed`、`blocked` 或 `hard-stop` |
| `model dtype` | 模型输入本身的数据类型 |
| `verification path` | fp32、full-quant int8 等独立验证路径，不等于模型 dtype |
| `value_domain` | 输入值域/输入数据特征，如 mixed、positive、negative、ties |

所有模式都使用本 Skill 自带的设计/验证模板；不得以公共目录中的其它算子文档作为模板或事实源。
