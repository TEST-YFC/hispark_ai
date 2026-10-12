# decision2 复用判定详细流程

SKILL.md step2 给出了 decision2 的判据与结论格式。本文说明候选来源、语义证据获取、TFLite 多 builtin 验证和同义词簇维护。不得新建与已有 PrimType 语义重复的通路，否则会重复实现 kernel/infer/coder 并增加维护成本。确切名称 0 命中只表示没有同名 PrimType，不能据此判定需要新建。

## 候选的四层来源（scan_op.sh「decision2 复用候选排查」段自动汇集）

1. **去版本后缀的基名**（`XxxV2` → `Xxx`）。
2. **schema union 双向子串命中**（候选名含目标名 / 目标名含候选名）。
3. **跨框架映射字典**——tf2onnx 的 `@tf_op` 注册表（TF/TFLite 名 ↔ ONNX 名的权威映射，对任意算子通用，是异名同义的主力来源）。其输出含 handler 的辅助算子，按链路概览与语义证据甄别主算子。
4. **同义词簇缓存**——历次 decision2 判定中确认过的等价族（scan_op.sh 内 `CLUSTERS` 表）。

人工检索发现 ①–④ 未列出的新等价族时，按格式向 `scan_op.sh` 的 `CLUSTERS` 表追加一行。该表用于跨会话保留已确认的等价关系，使后续扫描直接列出候选，避免重复检索。

## 人工语义检索（四层之外必补一轮）

- 拿 decision1 语义摘要的**核心语义**（条件选择、广播、索引、归约…）作关键词，检索 `schema/ops.fbs` 与 `tools/converter/parser/`——按"做什么"找，不按"叫什么"找。
- **源框架文档常直接写明等价关系**（"same as X with broadcasting"、"the broadcasting version of Y"）。decision1 见到此类表述，立即把被指算子作为候选跑一次 `scan_op.sh <候选名>`。

## 候选语义证据的取法

- **真值在仓内实现**：判定前必须 Read 候选的 ④infer 与 ⑤kernel（scan 候选段的「语义证据」行只是索引，不能代替通读），辅以已映射到该 PrimType 的框架规格（看它已有 parser 属于哪个框架，读那个框架的规格）。
- **禁止拿"与候选同名的其它框架算子"的摘要当候选语义**——同名异义是常态（见 lessons.md 决策期）。
- 一个 PrimType 的 kernel 可能按**输入个数分支处理多个形态**（如单输入坐标模式与三输入选择模式并存）——等价性**逐分支**判定，目标算子与某一分支逐项等价即复用该分支。

## 等价判据的边界

四条判据（输入个数/顺序/语义、输出语义、属性集、广播规则）是**逐项相等**，不是包含关系：

- **候选能力更强（超集）同样不等价**——非广播算子映射到全向广播 PrimType，"算得出来"但语义被放宽（本应拒绝的形状组合被静默放行、"仅 rank-1 条件"类约束消失），属缺陷不属复用。
- 反向（目标是广播版、候选是非广播版）是能力缺口，同样不等价。
- **判定与工期无关**：任何一条不符即不复用，不得以省工作量为由把不等价复用列为"备选方案"呈给用户——只能向用户说明判定结果。

## 可达性探针（TFLite 同族多 builtin / 疑似 converter 归一化时，判定前必做）

源框架可能根据输入形状为同一上层算子生成不同 builtin，例如同形输入生成非广播版，实际需要广播时生成广播版。输入形态对应哪个 builtin，决定该 builtin 的可达输入域，并影响 decision2 判定和各层工作量。若直接按文档中的全部语义判定，可能实现探针无法生成的形态，或把可达需求归到错误的 builtin。

方法：每类形状形态（同形 / 各广播形态 / 规格列明的特殊形态）各构建一个最小 TFLite 模型（`tf.function` 包裹目标 raw_op → `TFLiteConverter` 转出），解包核对 operator code：

```bash
python3 -c "from tensorflow.lite.python import schema_py_generated as s; \
m=s.Model.GetRootAsModel(open('<model.tflite>','rb').read(),0); \
print([max(m.OperatorCodes(i).BuiltinCode(),m.OperatorCodes(i).DeprecatedBuiltinCode()) for i in range(m.OperatorCodesLength())])"
```

生成「输入形态 → 实际 builtin」映射表并入 decision4 呈现。三条用法：

1. 每个 builtin **只为探针证实可达的形态**建链路、列能力清单与用例。
2. 探针逼不出的形态（典型：仅兼容 API 可达的特殊模式）列为**覆盖缺口，交由用户决定**，不自作主张扩 kernel/infer。
3. 该表直接复用为 op_spec 的 docstring 证据与 `TFLITE_TARGET_BUILTIN` 声明（一次探针，三处受益）。

环境无 TensorFlow 时（hs-verify-op-host 本就依赖它，正常都有），把"未探针、按文档全部语义判定"作为风险显式写进 decision4 报告。

多 builtin 同族时，同形输入通常落到非广播版，因此应优先保证非广播版链路完整。两版的专属语义可能互不包含；例如，非广播版特有的 rank-1 条件匹配首维模式不属于 numpy 广播，广播版不能表达该模式。各自的用例只覆盖各自规格列明的形态。
