# 训练 Host 验证

本分支验证 converter 生成的 Micro 训练 C 工程。完整 Lite runtime 的 `benchmark_train --trainModel=true` 可以作为额外对照，但不能替代这里的生成 C 验证。`target=RISCV` 的代码在本机编译执行仍是 Host，不是板端。

## 1. 计划与环境

完整工作流传入 `verification_kind=training`、代码根、`<opdir>`、训练单元、能力清单、工具包和本轮标识。`stage=plan` 只准备测试计划和生成器；`stage=run` 按已确定计划执行。独立 Host 请求先完成相同的计划步骤。

- 检查 Python、NumPy、参考框架、ONNX、CMake、Host C/C++ 编译器和已解压训练工具包；优先使用独立虚拟环境。
- 检查工具包与当前源码/构建一致，不能用旧 converter 验证新源码。记录源码 diff 指纹、converter 及静态库 hash。
- 训练源码路径和构建能力以当前仓库为准。检查 `train_mode=fp32`、loss/optimizer 配置、生成 benchmark、图和内存导出及 native CMake 开关，不从旧说明推断已支持。
- 计划生成器放 `<opdir>/scripts/train_case_spec.py`，案例放 `<opdir>/cases/<case_id>/`，运行放全新 `<opdir>/runs/<run_id>/<case_id>/`。用例先确定，不能边跑边删失败项。

## 2. 默认新建最小模型

每次默认生成新的最小训练模型。只有用户指定复用现有模型时才复用，并重新核对生成来源和初值。生成器承担具体算子的模型构造；固定 runner 承担转换、构建、执行和文件比较，不把某个算子的生成逻辑写进通用 runner。

最小结构按实际形状选已有支持层：

```text
输入 → 可训练上游层 → 被测算子 → 必要的分类头 → logits
                                                   ↓ converter 增加 loss/label
```

用上游权重更新验证梯度经过目标算子，不能只观察下游层权重。选择非零梯度输入和初值，参考第 1 步上游参数必须有可测变化。存在绕过目标的分支时，安排单路径用例或直接 dX 检查，避免旁路掩盖目标反向缺陷。

默认采用已支持的 FP32、静态形状、batch=1、SoftmaxCrossEntropy 和 SGD momentum=0 基线；同一个训练单元按数学能力补充：

- 正常与边界 shape/rank/axis/广播；有顺序区别的输入分别测试；
- T+T（两个激活）、T+C（结构常量或普通常量）、T+W（可训练参数），不适用的组合写原因；不能只根据 ONNX initializer 身份区分可训练与常量，须检查优化后的图和参数选择；
- branch fan-out 和梯度累加、可选输入、保活张量；
- 转换期应拒绝的动态维度、非法属性或其他明确不支持组合；
- 参数算子的冻结覆盖按第 6 节处理。没有参数的算子不凭空增加冻结逻辑。

### 模型与参考结果必须同源

1. 固定 Python、NumPy、参考框架 seed，禁用随机训练行为；记录依赖版本和模型生成脚本 hash。
2. 用同一个模型实例导出初始 ONNX，并保存初始 state。参考训练前不得随机重新初始化；导出与参考执行使用独立的状态副本也必须从这份初始 state 恢复。
3. 对 PyTorch 导出显式选择静态输入、`opset_version=13`、`dynamo=False`（以本机版本支持为准），检查最终 ONNX 目标节点及属性。参考框架的 label 可以转换为 long，给 Micro 的 label 文件使用实际接口要求的 int32；输入为 float32。
4. ONNX 一般只导出 logits 前向网络，由 `[train]` 注入 loss 和 label；不要重复导出 loss 又让 converter 添加一次。检查图中输入/label 的名字、顺序和数量。
5. 默认至少训练两步，记录固定样本序列，checkpoint 为 `0,1,<steps>`：0 是任何参数更新前，1 是一步更新后，最后一项是全部更新后。数值模式 warmup 必须为 0。
6. Predict 的参考输入是 benchmark 第一个训练样本，使用更新前权重；Eval 的输入和 label 固定，每个 checkpoint 在 eval 模式执行而不更新参数。参考 SGD 的学习率、momentum、weight decay、loss reduction 与生成代码保持一致。
7. 保存 Predict 完整输出、每个 checkpoint 的 Eval 完整输出和 loss、全部预期导出参数及名称/布局映射。若转换转置或改名，保存明确映射和依据，不按导出文件序号猜权重对应关系。

优先使用 PyTorch 同实例参考。参考框架缺失时，先记录依赖问题；对可独立推导的小模型，可以使用从同一初值生成的 NumPy 解析参考，并增加有限差分或独立等价性自检。必须说明替代参考的方法和局限，不写 PyTorch 已执行；复杂或无法独立核对的导数保持 NOT_RUN，不用被测 C 代码反算参考。

生成后锁定 `case.json` 与所有模型、输入、label、参考文件的 hash。模型生成失败单独记 `TRAIN_MODEL_GENERATE=FAIL`，不能改用手写 generated C 继续宣称通过。

## 3. 转换和结构检查

固定 runner 的输入和调用见 [训练 runner 使用说明](commands.md)。其转换必须使用真实 `converter_lite`，基本配置为：

```ini
[micro_param]
enable_micro=true
target=RISCV
support_parallel=false

[train]
train_mode=fp32
loss=softmax_cross_entropy
label_tensor_name=label
optimizer=sgd_with_momentum
learning_rate=0.01
momentum=0.0
batch_size=1
```

按当前配置解析器启用训练图/内存 dump，不猜测配置键。逐个检查：

- 目标 ONNX 节点到优化后 forward primitive 的对应关系，防止常量折叠或等价替换让测试绕过目标；
- `training_graph.dot` 中 Backward、GradAccum、optimizer 的 tensor/node 对应；
- `training_memory.json` 的对象类型、大小、保活时间、复用关系及所需 forward activation；
- 生成 `net0.c` 中实际 backward/kernel 调用，不能仅搜索某个符号名即判定正确；
- `net.cmake` 和独立工程中的新增头文件/源文件收集；
- 同一前向模型不带训练配置的转换，不应泄漏训练符号和 fp32_grad 源码。

结构检查保存到 `<run-dir>/generated-code-inspection.md`，每项绑定实际文件与 hash。预期拒绝用例要求 converter 非零退出且诊断符合预先指定的原因；依赖库找不到、崩溃等环境/实现错误不是预期拒绝。拒绝用例通过只表示边界检查通过，不计训练数值 PASS。

### 训练图检查要求

每个 numerical training case 必须声明 `graph_expectations_version=1` 和 `graph_expectations.targets`。默认梯度路径还必须声明非空 `upstream_paths`。每个 target 至少包含 `forward_name`、`forward_primitive` 和 `backward_symbols`，可声明 `backward_name`、`backward_primitive`。这些字段来自当前 case 生成器；runner 不针对任何具体算子自动补充或绕过检查。

转换成功后，`check_training_graph.py` 在编译前检查优化后的 `forward_graph.dot`、`training_graph.dot` 和生成的 `src/**/*.c`：目标 forward 节点唯一存在；训练图包含对应 ForwardRef/Backward；loss 到目标反向节点存在梯度路径；目标训练节点 ID 对应的 C 代码块包含声明的实际 backward 调用。证据写入 `graph_gate`，并绑定文件路径、大小和 SHA256。缺失、解析失败、节点被融合或只有注释而没有实际调用均为 FAIL。

`training.fusion_blacklists` 是用例的明确输入，按原样输出到 `[registry]`，禁止 runner 自动追加某个算子的融合黑名单。Windows Host 不因缺少 ONNX Python 包而跳过图检查；模型身份使用锁定的模型文件 hash，源节点范围由 case 的 expectations 和生成图节点共同校验。

聚合器会重新读取当前 run 的 `case.json` 和生成目录并复核图检查，不能信任 summary 中手写的 PASS。因而 numerical PASS 必须同时满足数值检查和 graph gate；reject case 仍只按预期 converter 错误判定，保持原有逻辑。

目标算子处于离散梯度边界时，case 可显式声明 `graph_expectations.gradient_barrier=true`。
此时图检查改用并列 FP32 上游路径和边界上游路径，数值检查必须包含边界权重
`barrier_unchanged/<name>` 与并列上游 `upstream_update/<name>`。这是受限配置，不是
通用任意梯度屏障能力；字段要求见训练 runner 使用说明。

## 4. 编译和真正执行训练

生成的 RISCV CMake 必须有 native 训练 benchmark 分支。runner 默认不指定并发，交给构建工具处理；可通过 `--jobs <正整数>` 显式指定。典型命令由 runner 固定执行：

```bash
cmake -S "$NET_DIR" -B "$NET_DIR/build"   -DPKG_PATH="$PKG_ROOT"   -DOP_LIB="$PKG_ROOT/tools/codegen/lib/cpu/libnnacl.a"   -DWRAPPER_LIB="$PKG_ROOT/tools/codegen/lib/cpu/libwrapper.a"   -DMS_ROOT_DIR="$PKG_ROOT" -DRISCV_TOOLCHAIN_PATH=   -DMSLITE_TRAIN_BENCHMARK=ON
cmake --build "$NET_DIR/build"
```

这里生成的是 `build/benchmark`，它使用训练 benchmark 模板；不是完整 runtime 的 `benchmark_train`。不通过改 generated C、替换公式或手动修改结果来修复被测源码。

benchmark 位置参数按当前模板核对：

| 参数 | 内容 |
|---|---|
| 1 | 第一个训练样本所有 input 和 label 文件，逗号连接 |
| 2–5 | steps、warmup=0、threads=1、bind=1 |
| 6 | 固定 Eval 的所有 input **及 label** 文件，逗号连接 |
| 7–8 | 空校准文件、余弦阈值占位；不作为数值 PASS 依据 |
| 9–10 | 更新后/更新前权重导出目录 |
| 11 | 训练序列文件，每行是一组 input+label 的绝对路径 |
| 12 | 数字 checkpoint 列表，如 `0,1,2`，不写字符串 final |
| 13–14 | checkpoint 和 Predict dump 目录 |

执行前创建所有导出目录，包括每个 checkpoint 的 `step_0000_weights` 等子目录。数值模式要求最后四个参数非空；训练序列行数必须等于 steps。只传第一个样本而不传序列与 dump 参数，不能得到本流程要求的证据。

## 5. 数值判定与汇总

- 使用完整二进制输出，不使用只打印前 10 个元素的控制台预览。
- 按 dtype、shape、元素数和字节数检查每份文件，拒绝缺项、额外未映射参数、NaN/Inf、截断和陈旧结果。名称映射必须一对一。
- 默认逐元素 `abs(actual-reference) <= atol + rtol*abs(reference)`，`atol=rtol=1e-5`。阈值变化必须在计划中说明对应项目和原因，不能看到失败后临时放宽。
- 训练权重 dtype 当前限定为 `float32|int32`。`float32` 使用上述容差；`int32` 使用
  逐元素整数精确相等，不套用浮点容差。
- 比较 Predict logits、checkpoint 0/1/final 的 Eval logits、loss 和参数；第 1 步参考与实际上游参数均要有非零变化并相互对齐。
- 直接梯度未导出时记录 `not_evaluated: raw_gradients`，结论为输出和参数更新对齐，不写“所有梯度逐元素通过”。若设计明确要求梯度单测，缺少直接梯度证据仍不满足计划。
- 有状态 optimizer 需额外核对多步状态规则；不能因为源码存在 Adam 就宣称已验证 Adam。基线使用的 SGD 参数范围与未测 optimizer 分开报告。

先用 `scripts/training/aggregate_training_results.py --export-board-expected` 按已锁定的 case 计划生成聚合报告和板端预期矩阵；缺少任一 summary 会自动记为 `NOT_RUN`，不会被忽略。`PASS` 只在所有数值 case 通过且预期拒绝项状态正确时产生。只有数值 PASS 用例进入板端矩阵；预期拒绝项保留在排除清单，不进入板端分母。

单 case 的 `train_summary.json` 由固定 runner 生成。结构检查与模型来源检查由执行者补充实际证据，runner 的数值 PASS 不会自动证明这些人工检查完成。聚合时在 `<opdir>/runs/<run_id>/train_verify_summary.json` 列出全部预期 case、测试点、类型、各阶段状态、summary 路径和 hash、结构检查、未测项，负向转换单列。缺少任一预期用例或必测项时 `TRAIN_HOST_VERIFY_GATE` 不能为 PASS。

失败保留首个真实错误。模型/GT/计划问题回到 plan 并更新设计；converter/GradRule/coder/kernel 问题回到实现；环境问题先修环境。重跑使用新目录，不覆盖失败记录。

## 6. 权重冻结用例

先读取 `hs-dev-train-op-implement` 的权重冻结说明并检查当前源码。`frozen_node`、参数选择或可选梯度接口不存在时，明确记录能力缺失：普通非冻结用例可以继续，要求冻结的用例不能记通过；不在验证阶段顺手改框架。

源码支持后，使用同一模型/初值生成未冻结与冻结对照，模型必须有依赖目标 dX 的可训练上游。核对配置节点名在优化后仍对应预期节点；错误名称和共享参数策略按实际解析行为设计，不假设全部被拒绝。

冻结验证分开证明：

1. 目标权重仍参与 forward，输出和 loss 与参考一致。
2. 冻结参数无参数梯度、optimizer 节点和对应 optimizer state；上游所需 dX 仍存在，GradAccum 不被误删。
3. 同一运行时冻结参数的前后完整快照相同；可训练上游参数更新非零并与参考一致。
4. 明确 canonical 权重 RAM、训练权重对象、optimizer state 的区别。不能把无 optimizer state 说成不占 RAM；buffer 策略以实际实现为准。
5. 核对导出 manifest 的参数集合。某冻结参数未被导出只表示缺少观测，不能证明它未变化；补只读观测后再作数值结论。

当前 Host 文件导出接口不等于板端串口观测接口。板端所需快照另按板端训练步骤实现和检查。

## 7. 与文档结果同步

聚合报告使用 `schema_version=1`、`verification_kind=training`、`run_id`、`status` 和完整 `cases`。每行保留 case_id、kind、test_point、status、reason，以及单 case summary 的相对路径和 SHA256。详细字段见 `hs-design-op-manual/references/training/facts-schema.md`。

必需来源/结构检查至少记录 `package_source_freshness`、`target_backward_path`、`training_graph_and_memory`、`inference_isolation`，每项写状态、原因及实际证据。缺少前置时也生成本轮完整矩阵，未执行 case 为 NOT_RUN，已失败 case 保留 FAIL；不得因不能运行而省略验证文档。
