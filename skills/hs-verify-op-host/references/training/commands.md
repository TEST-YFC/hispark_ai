# Host 训练执行器

`run_training_case.py` 运行一个已确定的 ONNX FP32 训练用例：转换为 Micro C、native 编译、执行训练，并逐元素比较完整输出、loss 和参数。它不生成模型或参考数组；会独立解析源 ONNX，并在转换后、构建前执行目标节点保留、训练关键链及生成 C 调用检查。它不证明工具包对应当前源码，也不证明任意训练图/内存语义正确；完整审计仍按 [训练验证步骤](workflow.md) 完成。

当前执行范围：Linux/WSL、batch=1、静态 shape、FP32 数据、int32 稀疏分类标签、softmax cross entropy、SGD with momentum。训练权重当前只接受 `float32` 和 `int32`；`int32` 权重按整数精确相等判定。其他 loss、batch、dtype、optimizer、TFLite 不在此脚本的已实现范围；遇到这些需求先报告范围差异，不要强行套用。本脚本依赖 Python 3.10+、NumPy、ONNX Python 包、CMake、C/C++ 编译器和同一版本的 converter/静态库。

## 用法

```bash
python3 <host_skill_root>/scripts/training/run_training_case.py \
  --case <opdir>/cases/<case_id>/case.json \
  --pkg <current-source-package> \
  --run-dir <opdir>/runs/<run_id>/<case_id>
```

单条命令默认超时 300 秒，可用 `--timeout <秒>` 调整；超时保留日志并记录 FAIL，Linux/WSL 会终止该命令的进程组。Windows 原生构建不在此执行器当前支持范围。

`--run-dir` 必须尚不存在，不能复用空目录或旧结果。成功退出码为 0；FAIL/NOT_RUN 返回 2。脚本写入 `train_summary.json`，但不生成整个用例矩阵的聚合报告。

## case.json

以下是字段示意。`sha256` 要由实际文件计算，不能直接执行占位值；路径相对 case.json 所在目录解析，所有模型、输入、标签和参考文件必须归档在该 case 目录内，不能引用目录外文件。

```json
{
  "schema_version": 1,
  "verification_kind": "training",
  "case_id": "TC_001",
  "kind": "numerical",
  "test_point": "静态 FP32 反向传播与上游参数更新",
  "model": {"path": "model.onnx", "sha256": "实际SHA256"},
  "graph_expectations_version": 1,
  "graph_expectations": {
    "targets": [{
      "source_node": {"name": "<source_target_node_name>", "op_type": "<onnx_op_type>", "domain": ""},
      "forward_name": "<forward_target_node_name>",
      "forward_primitive": 0,
      "backward_name": "<backward_target_node_name>",
      "backward_symbols": ["<backward_kernel_symbol>"]
    }],
    "upstream_paths": [{
      "forward_upstream": {"name": "<forward_upstream_node_name>"},
      "forward_target": {"name": "<forward_target_node_name>", "primitive": 0},
      "upstream_backward": {"name": "<backward_upstream_node_name>"},
      "optimizer": {"name": "<upstream_optimizer_node_name>"}
    }]
  },
  "training": {"steps": 2, "learning_rate": 0.01, "momentum": 0.0,
               "label_tensor_name": "label", "frozen_nodes": []},
  "sequence": [
    {"inputs": [{"path": "x0.bin", "sha256": "实际SHA256", "dtype": "float32", "shape": [1, 3]}],
     "labels": [{"path": "y0.bin", "sha256": "实际SHA256", "dtype": "int32", "shape": [1]}]},
    {"inputs": [{"path": "x1.bin", "sha256": "实际SHA256", "dtype": "float32", "shape": [1, 3]}],
     "labels": [{"path": "y1.bin", "sha256": "实际SHA256", "dtype": "int32", "shape": [1]}]}
  ],
  "eval": {
    "inputs": [{"path": "eval_x.bin", "sha256": "实际SHA256", "dtype": "float32", "shape": [1, 3]}],
    "labels": [{"path": "eval_y.bin", "sha256": "实际SHA256", "dtype": "int32", "shape": [1]}]
  },
  "reference_source": "独立参考实现、版本和同一初始化模型的生成方式",
  "golden": {"path": "golden.npz", "sha256": "实际SHA256"},
  "outputs": [{"index": 0, "shape": [1, 4], "role": "logits"},
              {"index": 1, "shape": [1], "role": "loss"}],
  "weights": [{"name": "实际导出参数名", "reference": "wup", "dtype": "float32", "shape": [3, 4]}],
  "upstream_weights": ["实际导出参数名"],
  "frozen_weights": []
}
```

上例使用通用占位，不对应任何具体算子，不能直接运行。所有 `<...>` 必须按当前源 ONNX、转换图和生成代码对应的明确预期填写；两个 primitive 字段中的 `0` 仅为保持 JSON 整数类型的占位，必须替换为实际 primitive 编号。`domain: ""` 表示预期默认 domain；非默认域须显式填写实际预期值。`forward_target` 的名称和 primitive 须与对应 target 一致。不得照搬占位、编号或符号，也不得将本次检查读出的实际值自动回填充当事先声明的预期。新 numerical case 必须按下文声明完整 `source_node`。

训练序列长度必须等于 steps，且至少两步；每步与 Eval 的输入顺序、dtype、shape 一致。输出下标连续，最后一个是 loss。参数名须与当前生成工程的导出 manifest 一一对应；若转换后的 layout 不同，先确定映射、更新计划和独立参考，不能为了让比较通过而盲目转置。

`golden.npz` 包含下列数组，shape 与声明一致。输出和 loss 是 float32；训练权重按 case
声明为 float32 或 int32。int32 权重逐元素整数相等，不使用浮点容差；int32 输出不在当前范围：

```text
predict/output_0
step_0/output_0    step_0/output_1    step_0/weight/wup
step_1/output_0    step_1/output_1    step_1/weight/wup
step_2/output_0    step_2/output_1    step_2/weight/wup
```

上例 steps=2；其他步数的最后一组用实际数字替换 2。多个 logits 或权重按声明扩展。Predict 使用**第一个训练输入和初始权重**；checkpoint 输出使用 Eval 输入和标签。checkpoint 0 在更新前，1 在一步更新后，最后一个在全部更新后。

## 转换、构建与训练

配置由脚本写入 `micro_train.cfg`：`[micro_param]` 中设置 `target=RISCV`、`enable_micro=true`；`[train]` 中设置 `train_mode=fp32`、`dump_training_graph=true`、loss、optimizer、学习率等。真实 converter 命令为：

```bash
converter_lite --fmk=ONNX --modelFile=<model.onnx> \
  --configFile=<micro_train.cfg> --outputFile=<run-dir>/net
```

CMake 用包内 `libnnacl.a`、`libwrapper.a` 及 `MSLITE_TRAIN_BENCHMARK=ON` 构建 native 工程。可执行文件是 `net/build/benchmark`。Host 的 RISC-V 代码生成路径在 x86 执行，不能据此写板端通过。

benchmark 按位置传入 14 个参数：

```text
1  首个训练样本的 input(s),label
2  steps
3  0（warmup）
4  1（threads）
5  1（bind）
6  Eval 的 input(s),label
7  空字符串
8  0.9999（不作为本流程的数值通过标准）
9  after 目录
10 before 目录
11 sequence.txt
12 0,1,实际最终步数
13 checkpoints 目录
14 predict 目录
```

脚本创建导出目录及每个 checkpoint 权重子目录，检查完整二进制文件。默认 `atol=rtol=1e-5`；拒绝缺项、错 shape/dtype/字节数、非有限值、错误参数映射和零上游更新。

## 负向与未执行结果

拒绝用例使用 `kind="reject"`，保留版本、类型、case_id、test_point、model 和 training 字段，并提供 `expected_error` 精确诊断片段。只有 converter 实际非零退出且匹配诊断才可写 `PASS_EXPECTED_ERROR`；它不是训练数值 PASS。不要把缺包、命令不存在或崩溃当成预期拒绝。

缺 converter、静态库或 native 工具时记录 `NOT_RUN`。配置解析、构建、执行、证据或比较失败记录 `FAIL`。`numerical_pass=true` 只表示此执行器完成的数值检查；`not_evaluated` 保留未覆盖的源码版本、完整图/内存语义、原始梯度、板端检查；其中图/内存语义不等于下述已执行的结构门禁。

只有当前源码支持冻结时，才生成 `frozen_nodes` 配置。所有冻结参数须有真实运行时快照和完整映射；导出缺少某个参数不等于该参数未变化。

## 全量聚合

单 case 完成后，用已锁定的计划生成聚合结果：

```bash
python3 <host_skill_root>/scripts/training/aggregate_training_results.py \
  --opdir <opdir> --run-id <run_id> --expected <opdir>/cases/expected.json \
  --export-board-expected
```

输出固定为 `<opdir>/runs/<run_id>/train_verify_summary.json`。缺少 case 会记录为 `NOT_RUN`，退出码非 0；聚合结果不能绕过文档审计。增加 `--export-board-expected` 后，还会在 `<opdir>/runs/<run_id>/board_expected/` 写入逐 case expected 和 `training_board_expected_matrix.json`；该目录必须为空或不存在，工具拒绝覆盖旧结果。

## Graph gate

### 新 case 的源节点与图预期

每个新 `kind="numerical"` 用例必须声明 `graph_expectations_version: 1` 和非空 `graph_expectations.targets`。默认路径还必须声明非空 `graph_expectations.upstream_paths`。每个 target 必须完整填写：

- `source_node.name`：源 ONNX 中唯一节点的精确名称。
- `source_node.op_type`：预期的 ONNX `op_type`，非空字符串。
- `source_node.domain`：预期的 ONNX domain，必须显式填写；默认 domain 写 `""`，不自动补为其他字符串。
- `forward_name`、`forward_primitive`：转换后 forward 节点的名称及 primitive。
- 非空 `backward_symbols`：允许的反向 kernel 符号，至少一个须在对应生成代码块中真实调用。`backward_name` 默认等于 `forward_name`；`backward_primitive` 可选。

完整对象示例见上方 case.json。提供 `source_node` 对象后，三个源字段缺一不可，且不接受额外字段；名称必须唯一，`op_type` 或 `domain` 不匹配都会 FAIL。这些是生成用例时锁定的预期，不能把运行时读取的实际值自动回填后声称完成预期比对，也不能用转换图 primitive 推测源 `op_type/domain`。

`upstream_paths` 每项声明 `forward_upstream`、`forward_target`、`upstream_backward`、`optimizer`。`forward_target` 必须唯一绑定已声明的 target。检查包含源模型 upstream→target、生成 forward 的 upstream→target、对应训练 ForwardRef→loss，以及 loss→目标 backward→上游 backward→ParameterGrad→optimizer。仅有任意 control 路径不能替代 ParameterGrad；绕行检查只屏蔽本项 target 的 backward，不能借其他 target 掩盖 loss 到上游 backward 的绕行。

### 离散梯度边界用例

目标算子本身没有连续梯度、但 forward 仍参与 loss 时，可声明受限的
`graph_expectations.gradient_barrier=true`。此时不使用默认 `upstream_paths`，而必须声明：

- 非空 `parallel_upstream_paths`：每项含 `forward_upstream`、`forward_sink`、
  `upstream_backward`、`parameter_grad`、`optimizer`，证明另一条 FP32 可训练路径仍有
  loss→Backward→ParameterGrad→optimizer 链路；
- 非空 `barrier_upstream_paths`：每项含 `forward_upstream` 和 `forward_target`，
  证明源模型中边界上游确实连到目标；
- 非空 `barrier_weights`：这些权重必须出现在 `weights` 中，且不能列入
  `upstream_weights`；它们表示梯度不继续传播的边界权重，不是冻结配置；
- `barrier_grad_slot_contains`：训练图中用于定位目标梯度槽的稳定文本；
- `forward_refs`、`forbidden_backward_nodes`、`forbidden_parameter_grads`、
  `forbidden_optimizers` 和 `required_code_calls`：按当前图和生成 C 声明应存在的
  证据与禁止出现的节点。

该配置用于验证 loss gradient 在声明的离散算子边界停止，同时并列 FP32 路径仍可更新。
数值侧必须生成 `barrier_unchanged/<weight>` 和 `upstream_update/<weight>` 检查。不要把
它写成通用任意梯度屏障或通用混合精度训练能力。

`training.fusion_blacklists` 是明确输入，原样透传；runner 不自动追加任何算子特例。目标被融合掉时，即使数值相同也必须 FAIL。

### 旧 case 兼容与 ONNX 依赖边界

为只读复审既有 schema-1 证据，代码仍接受未声明 `source_node` 的旧 numerical case，**这不是新用例的推荐或允许省略规则**。旧 case 仍须重新读取并核对模型 SHA、实际解析 ONNX、运行模型检查，以 `forward_name` 唯一匹配源节点并验证上游拓扑。其实际 `name/op_type/domain` 会记录在源检查结果中，`declared_identity_checked=false`；只能报告“已解析源模型并验证节点名/拓扑”，不能报告“已比对预期 op_type/domain”。完整声明且比对通过时该标记才为 `true`。不要为了补字段改写已锁定的历史 case、summary 或日志。

执行 numerical runner 和独立聚合复审的 Python 环境均须具备 `onnx` 包，包括在 Windows 上复审 WSL 生成的证据时；缺少依赖明确失败，没有静默跳过或 allow 模式。当前不支持 external-data ONNX：外部 tensor 文件没有单独锁定的身份链，模型不会被当成受支持的 numerical 输入放行。请为新用例生成数据内嵌的单文件 ONNX，并重新计算 SHA。`kind="reject"` 继续使用现有预期错误路径，不因源模型无法解析而提前取代 converter 的拒绝测试。

### 标准 Serializer 的 C 调用取证范围

转换后、构建前，`check_training_graph.py` 检查 `forward_graph.dot`、`training_graph.dot` 和 `net/src` 下的生成 C。节点 label 按行字段精确匹配，不把 `Target_other` 当作 `Target`，也不把 `prim=165` 当作 `prim=16`。

C 中的 `/* train_node_id=<id> kind=<kind> name=<name> */` marker 必须位于函数内，按节点 id 和名称唯一对应目标。取证限于同一文件、同一函数和 marker 所属作用域，遇到下一 marker 或该作用域结束即停止。声明、注释、字符串、`sizeof`，以及其他文件/函数/已结束作用域中的同名调用不能充当证据。

支持标准 Serializer（包括 `CodeFunctionWithCheck` / `CodeFunctionWithRet`）生成的以下形式；每条是独立示例，不表示应重复调用同一 kernel：

```c
Kernel(x, y);
if (Kernel(x, y) != NNACL_OK) { return NNACL_ERR; }
if (Kernel(x, y) != RET_OK) { return RET_ERROR; }
ret = Kernel(x, y);
int ret = Kernel(x, y);
return Kernel(x, y);
```

因此非 void kernel 不必改成 direct call 才能通过。检查器是针对这些生成形式的轻量识别，不是通用 C 解析器、预处理器或任意程序执行语义证明；新的宏封装或表达式形式不能默认视为已支持，应先增加相应正负测试再扩充识别。

### 证据复核

源检查结果记录于 `source_graph`，生成图/C 检查记录于 `graph_gate`；缺失节点、断链、缺少真实调用或过期证据均 FAIL，不能用 numerical PASS 替代。aggregator 重新读取当前 run 的归档 case，并通过相同 SHA 的原 case evidence 找回原目录；模型相对原 case 而非 run 目录解析。随后独立检查源 ONNX、重跑图门禁并比较完整 DOT/C 路径与 SHA 集合。

跨 Windows/WSL 复审仅支持明确的 `/mnt/<drive>/...` 与 `<drive>:/...` 同盘符映射，并保持原 case 在 opdir 内、模型在原 case 目录内、生成图/C 在当前 net 内的边界。不会搜索替代目录、修改 SHA 或重写旧 summary。源依赖及结构检查通过并不替代全量数值比较、完整语义审计或板端验证。
