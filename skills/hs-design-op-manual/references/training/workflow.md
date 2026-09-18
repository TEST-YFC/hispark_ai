# 训练文档流程

本分支生成两份独立文档：设计文档解释支持范围和实现方案，验证文档记录测试计划与本轮结果。不执行模型转换、训练或板测。

## 1. 阶段与输入

沿用入口中的模式名称，但训练按本文件执行：`integrated-initial` 对应 `publication=initial`，`integrated-final` 对应 `publication=final`。独立生成、更新或文件同步也须明确是初稿还是终态；只分析模板不写文件。

1. 核对调用方提供的代码根、绝对 `<opdir>`、算子名、`framework_scope` 和本轮 `run_id`。
2. 读取 prepare 的前向前置、反向设计、训练链路、实现计划，以及 Host plan 的用例生成器和 `case.json`。不自行编造缺失的规格或执行结果。
3. 按 [事实与审计规则](facts-schema.md) 生成 `docs/operator-training-manual-facts.json`。初稿写已核实的设计和待执行计划，不能写训练数值已通过。
4. 根据 [设计模板](operator-design-doc-template.md) 和 [验证模板](operator-verify-doc-template.md) 整理内容，生成两份候选。**设计初稿审核、发布后，才进入正式训练源码实现。**
5. 终态读取本轮全部用例结果与聚合报告，更新验证文档。缺工具包、冻结能力缺失、Host 失败或无板卡，都应写出状态、原因和恢复条件。
6. 审核事实、候选内容、完整用例表、敏感信息，再成对发布。文档审计通过只表示内容同步，不代表 Host 或板端通过。

结果位置固定：

```text
<opdir>/cases/<case_id>/case.json
<opdir>/runs/<run_id>/<case_id>/train_summary.json
<opdir>/runs/<run_id>/train_verify_summary.json
```

不从其他 run 或旧目录补 PASS。初稿的 `generated-code-inspection.md` 可以是待执行检查计划，终态必须区分实际观察和未执行项。

## 2. 生成候选并审计

```bash
python3 <manual_skill_root>/scripts/training/audit_manual_inputs.py \
  --opdir <absolute-opdir> \
  --facts <absolute-opdir>/docs/operator-training-manual-facts.json \
  --design <absolute-opdir>/docs/design.candidate.md \
  --verify <absolute-opdir>/docs/verify.candidate.md \
  --publication initial --render-candidates
```

候选路径必须不存在，脚本不覆盖已有文件。终态使用新候选名和 `--publication final`。省略 `--render-candidates` 只检查已有候选。

脚本逐项检查来源 hash、case 身份、聚合矩阵和每个单 case summary，候选正文须与 facts 渲染内容一致。若要改正文，先修改有来源依据的 facts，再生成新候选。脚本不能判断任意设计描述是否符合数学和源码，执行者仍须核对设计内容及证据，不得把脚本检查称为源码正确性证明。

## 3. 发布

公开正文用仓库或 `<opdir>` 相对路径，不写个人目录、账号、密钥、内部单号或私有链接。命令、原始日志可保存在证据目录，正文只列必要的相对索引。

当 `TRAIN_MANUAL_FACTS_SYNC`、`TRAIN_MANUAL_CONTENT_SYNC`、`TRAIN_MANUAL_CASE_SYNC` 均为 PASS 时：

1. 为已有两份目标分别建立可识别备份；不存在的目标记为不存在。
2. 依次替换 `<opdir>/docs/{op}-operator-design-doc.md` 和 `{op}-operator-verify-doc.md`。两次文件替换不是天然原子操作。
3. 任何一步失败，恢复发布前状态；不删除其他文件。
4. 重新读取两份目标，用同一 facts 复跑审计。成功才输出 `TRAIN_OP_MANUAL_SYNC=PASS`，否则恢复并输出 FAIL。

训练为 FAIL、NOT_RUN 或 BLOCKED 时，只要文档真实、来源完整，文档同步仍可以 PASS。缺少冻结能力时阻止“冻结训练已通过”的结论，不阻止发布如实说明阻塞的文档。
