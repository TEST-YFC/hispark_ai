# Host workflow gates

目录：

- [使用方式总览](#使用方式总览)
- [流程地图](#流程地图)
- [workflow 模式的 pre-verify 门禁](#workflow-模式的-pre-verify-门禁)

以下内容从入口按需下沉，用户可见步骤和门禁不变。

## 使用方式总览

这个 skill 做的是**测试设计与 Host 验证**,不是实现算子。它要求先写/对账 `op_spec.py`,再由固定 harness 生成模型、运行
MindSpore Lite、比对真实输出,最后只按 harness 的 `VERDICT`、`HARNESS_EXIT`、Excel 和 `verify_summary.txt`
汇报结论。

对用户展示当前进度时,使用 todo 样式,不要只说“正在第几步”：

```markdown
- [ ] step0 准备工具链与项目目录
- [ ] step1 standalone编写 / workflow只读对账 `<proj>/scripts/op_spec.py`
- [ ] step2 运行固定 harness
- [ ] step3 读取 `VERDICT` / `HARNESS_EXIT` / Excel / `verify_summary.txt`
- [ ] step4 排查失败或签收结论
```

推进时只更新状态,并附一句当前证据。例如：

```markdown
- [x] step0 准备工具链与项目目录
- [x] step1 standalone编写 / workflow只读对账 `<proj>/scripts/op_spec.py`
- [ ] step2 运行固定 harness - 正在等 `wait_verify.sh` 返回 VERDICT
- [ ] step3 读取 `VERDICT` / `HARNESS_EXIT` / Excel / `verify_summary.txt`
- [ ] step4 排查失败或签收结论
```

## 流程地图

| 阶段 | 做什么 | 成功证据 |
|---|---|---|
| step0 准备工具链与项目目录 | 确认 `MSLITE_PKG` 指向已解压构建产物,算子项目位于 `$MSLITE_OP_OUTPUT/<op>` | `converter_lite` 可执行,`op_spec.py` 不在 MindSpore Lite 源码/构建树内 |
| step1 准备 spec | standalone任务按规格编写`<proj>/scripts/op_spec.py`；完整workflow只读对账stage1冻结文件并运行pre-verify两道机械门禁 | `OP_NAME`、两套`*_TEST_CASES`、builder、`make_inputs()`齐全且门禁PASS |
| step2 运行 harness | 用 `run_all_cases.py --spec <abs path>` 执行 | 日志出现 `VERDICT` 和紧随其后的 `HARNESS_EXIT=N` |
| step3 读取结果 | 只读取 harness 产物,不要自行判定 | `verify_summary.txt`、每框架 Excel、`output/<framework>/tc*/output/<path>/stderr.log` |
| step4 排查或签收 | 非零退出按失败类型排查;全绿才签收 | 向用户照抄 VERDICT/退出码,列出 FAIL 证据或 PASS 报告 |

### Harness 内部 step1-step5

`run_all_cases.py` 对每条用例强制串行执行内部 step1-step5。这里的 step1-step5 是 harness 内部路径,
不要和上面的用户可见 step0-step4 混用：

| 内部步骤 | harness 做什么 |
|---|---|
| step1 | 构建模型、生成确定性输入、用 onnxruntime（CPU provider 明确 `NOT_IMPLEMENTED` 时回退 ONNX 官方 `ReferenceEvaluator`）/ tf.lite 计算参考输出 |
| step2 | 调 `converter_lite` 生成 micro C 工程 |
| step3 | `cmake` + `make` benchmark |
| step4 | 写入输入 `.bin` |
| step5 | 跑 benchmark 打印输出张量,再由 Python 统一计算余弦 |

### workflow 模式的 pre-verify 门禁

当`<proj>`来自完整算子workflow时，读取stage1已冻结的`op_spec.py`并与capability checklist
只读对账；启动harness前必须执行：

```bash
python3 <hs-dev-op-implement skill root>/scripts/gate_artifacts.py \
  --opdir <absolute proj> --op <Op> --stage pre-verify --framework <framework>
python3 <hs-verify-op-host skill root>/scripts/validate_op_spec.py <absolute proj>
```

每个激活 framework 都要得到 `ARTIFACT_GATE=PASS`，且 validator 退出码为 0。前者确认实现合同、已有能力 review、能力清单和测试 spec 没有断链；后者在长转换前拦截动态输入数量、initializer 声明、capability case ID 及 ONNX `auto_pad/pads` 冲突。独立 Host 任务没有实现工作区时不伪造这些产物，但仍执行 harness 内建的 spec、目标算子身份和能力覆盖门禁。

harness 只要求所选 framework 的模型 builder：`--framework onnx` 必须定义
`build_onnx_model`，但不得强制不存在的 TFLite 路径提供 `build_tflite_model`；TFLite 同理。
`--framework all` 才同时要求两套 builder。公共的算子名、两套 case 容器和 `make_inputs()`
仍是固定 spec 契约，范围外框架的 case 容器应为空。

完整workflow的Host阶段不得直接新增、删除或改写case。若对账发现模型构造、输入/GT、case或
覆盖映射必须变化，返回顶层workflow的stage1，重新prepare、生成初版文档、通过pre-source并
重跑apply/build；不能在Host阶段改完`op_spec.py`后继续使用旧facts哈希。

`ARTIFACT_GATE=PASS` 还要求实现工作区存在编码后 `docs/code-review.md`。该审查必须覆盖注册
键与 dtype 分支可达性、量化器列表归属、常量折叠/节点重写双路径和生成代码调用；没有审查
文件或存在未处置 `FIX_REQUIRED` 时，禁止启动长转换。这样可以在 Host 之前拦截“注册了
uint8/int8 但 coder 未分支”“永不执行死代码”“量化项落错白名单”“Fill 被折叠后误报
原算子已执行”等结构性问题。
