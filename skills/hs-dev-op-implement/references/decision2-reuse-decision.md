# decision2 复用裁决详细流程

SKILL.md step2 给出了 decision2 的判据与结论格式；本文是完整操作流程：候选从哪来、语义证据怎么取、TFLite 多 builtin 怎么实证、同义词簇怎么维护。**新建一条与已有 PrimType 语义重复的完整通路（双倍 kernel/infer/coder、双倍维护面）是 decision2 要防住的最大浪费**——确切名 0 命中只说明"没有同名 PrimType"，不构成"需要新建"的结论。

## 候选的四层来源（scan_op.sh「decision2 复用候选排查」段自动汇集）

1. **去版本后缀的基名**（`XxxV2` → `Xxx`）。
2. **schema union 双向子串命中**（候选名含目标名 / 目标名含候选名）。
3. **跨框架映射字典**——tf2onnx 的 `@tf_op` 注册表（TF/TFLite 名 ↔ ONNX 名的权威映射，对任意算子通用，是异名同义的主力来源）。其输出含 handler 的辅助算子，按链路概览与语义证据甄别主算子。
4. **同义词簇缓存**——历次 decision2 裁决确认过的等价族（scan_op.sh 内 `CLUSTERS` 表）。

**簇缓存自维护**：人工检索发现 ①–④ 都没列出的新等价族时，按格式把它追加进 scan_op.sh 的 `CLUSTERS` 表（一行）。这是 skill 替代跨会话 memory 的累积机制——让下一个会话机械命中，不再重复人工检索。

## 人工语义检索（四层之外必补一轮）

- 拿 decision1 语义摘要的**核心语义**（条件选择、广播、索引、归约…）作关键词，检索 `schema/ops.fbs` 与 `tools/converter/parser/`——按"做什么"找，不按"叫什么"找。
- **源框架文档常直接写明等价关系**（"same as X with broadcasting"、"the broadcasting version of Y"）。decision1 见到此类表述，立即把被指算子作为候选跑一次 `scan_op.sh <候选名>`。

## 候选语义证据的取法

- **真值在仓内实现**：裁决前必须 Read 候选的 ④infer 与 ⑤kernel（scan 候选段的「语义证据」行只是索引，不能代替通读），辅以已映射到该 PrimType 的框架规格（看它已有 parser 属于哪个框架，读那个框架的规格）。
- **禁止拿"与候选同名的其它框架算子"的摘要当候选语义**——同名异义是常态（见 lessons.md 决策期）。
- 一个 PrimType 的 kernel 可能按**输入个数分支承载多个形态**（如单输入坐标模式与三输入选择模式并存）——等价性**逐分支**裁决，目标算子与某一分支逐项等价即复用该分支。

## 等价判据的边界

四条判据（输入个数/顺序/语义、输出语义、属性集、广播规则）是**逐项相等**，不是包含关系：

- **候选能力更强（超集）同样不等价**——非广播算子映射到全向广播 PrimType，"算得出来"但语义被放宽（本应拒绝的形状组合被静默放行、"仅 rank-1 条件"类约束消失），属缺陷不属复用。
- 反向（目标是广播版、候选是非广播版）是能力缺口，同样不等价。
- **裁决与工期无关**：任何一条不符即不复用，不得以省工作量为由把不等价复用列为"备选方案"呈给用户——可呈报的只有裁决结果本身。

## 可达性探针（TFLite 同族多 builtin / 疑似 converter 归一化时，裁决前必做）

源框架可能按输入形状对同一上层算子择优发不同 builtin（同形发非广播版，真广播形状才发广播版）。「哪个输入形态实际落到哪个 builtin」决定每个 builtin 的**真实输入域**，直接改写 decision2 裁决与各层工作量——按文档语义全集裁决，会把探针逼不出的不可达形态当需求实现（kernel/infer/coder 全白做），又把真实需求分错家。

方法：每类形状形态（同形 / 各广播形态 / 规格列明的特殊形态）各构建一个最小 TFLite 模型（`tf.function` 包裹目标 raw_op → `TFLiteConverter` 转出），解包核对 operator code：

```bash
python3 -c "from tensorflow.lite.python import schema_py_generated as s; \
m=s.Model.GetRootAsModel(open('<model.tflite>','rb').read(),0); \
print([max(m.OperatorCodes(i).BuiltinCode(),m.OperatorCodes(i).DeprecatedBuiltinCode()) for i in range(m.OperatorCodesLength())])"
```

产出「输入形态 → 实际 builtin」映射表并入 decision4 呈现。三条用法：

1. 每个 builtin **只为探针证实可达的形态**建链路、列能力清单与用例。
2. 探针逼不出的形态（典型：仅 legacy API 可达的特殊模式）列为**覆盖缺口报告用户裁决**，不自作主张扩 kernel/infer。
3. 该表直接复用为 op_spec 的 docstring 证据与 `TFLITE_TARGET_BUILTIN` 声明（一次探针，三处受益）。

环境无 TensorFlow 时（hs-verify-op-host 本就依赖它，正常都有），把"未探针、按文档全集裁决"作为风险显式写进 decision4 报告。

两个结构性推论（多 builtin 同族时）：**非广播版是公共地带的收敛目标**（用户上层无论写哪个 op，同形输入都落到它），优先保证其链路完整；**两版的"专属语义"可能互不包含**（如非广播版特有的"rank-1 条件匹配首维"模式不属于 numpy 广播，广播版反而表达不了），各自用例只覆盖各自规格列明的形态。
