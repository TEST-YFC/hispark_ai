# 权重冻结能力与交接

本文件描述训练实现技能在 step0–step5 对冻结权重的核查边界。它是待实现能力的检查与交接规则，不表示当前
MindSpore Lite Micro 已经支持 `frozen_node`。必须以当前代码的真实文件和行号为准；不能用本文件向用户承诺
现成冻结能力。

## 1. 语义边界

冻结一个 forward node 的可训练权重，应该意味着：

- 权重仍参与 forward；
- backward 仍可产生需要的 activation gradient，使更上游可训练层能更新；
- 该权重不产生 parameter gradient、不分配 optimizer state、不进入 mutable train-weight update buffer；
- 不因为缺少 dW 就删除仍然需要的整个 backward node。

`canonical/default weight` 与 `mutable train-weight RAM` 是两个概念。冻结验收必须分别记录：

1. 权重是否仍有 canonical/default 数据和运行时 RAM 映射；
2. 是否被标记为可更新训练权重；
3. 是否有 parameter grad、optimizer state 和更新入口；
4. ExportWeight 导出的是哪一份实际数据。

保留 canonical RAM 不等于允许更新；导出文件存在也不等于权重被更新。

## 2. step0 能力矩阵

对用户明确要求冻结的任务，逐项记录 `AVAILABLE`、`MISSING` 或 `NOT_RUN`，附真实文件:行号：

| 能力 | 必须回答的问题 |
|---|---|
| parser | `[train]` 是否接受冻结配置并保存到训练参数？未知键是否拒绝？ |
| selection | 是否按真实 forward node name 选择该 node 拥有的 train weight？ |
| graph builder | 是否仅去掉冻结参数梯度，同时保留所需 activation gradient/backward node？ |
| helper | 缺失 dW/dB 是否可映射为 `NULL`，并与空地址错误区分？ |
| coder | Prepare 是否只校验实际存在的可选梯度？ |
| memory | 是否排除 optimizer state 和 mutable update buffer？canonical RAM 是否仍保留？ |
| kernel | 每个可选输出是否独立判空，判空前无访问？ |
| export | manifest、名称、shape、dtype、实际运行时数据是否可观察？ |

任一关键能力缺失时，输出 `TRAIN_IMPLEMENT_GATE=BLOCKED`，原因必须是
`weight-freezing-framework-capability-missing`，并请求用户确认框架变更。不得通过只改某个算子 coder 或
kernel 伪造冻结支持。

如果任务没有冻结要求，普通非冻结实现可以继续。能力状态照实记录；本次没有执行冻结验证时在交接中明确：

```text
weight_freezing=NOT_REQUESTED
```

不得把普通训练 PASS 扩大为冻结 PASS。

## 3. 地址和 kernel 规则

必选梯度（例如 dY，以及确实由图要求的 dX）使用必选地址解析；缺失是错误。可能因冻结而不存在的 dW、dB
使用可选地址 helper：

- 无效 gradient ID → `NULL`，表示有意省略；
- 地址解析失败 → 空字符串或错误状态，必须失败；
- `NULL` 不能当成空地址错误。

coder 和 kernel 不读取 `frozen_node`，不按 node name 自行决策。TrainingGraph 是唯一可信来源。
kernel 接口只按指针是否为空决定是否计算对应输出，并分别保护 dX、dW、dB 的读写、清零和累加。

若框架没有可选地址 helper，冻结任务停止在 step0；不要在单算子中添加局部替代语义。

## 4. 导出与实际快照验收

ExportWeight 的证据至少包括：

- 导出 API 和 generated export function 的路径；
- 导出对象列表、runtime address、canonical/default source 的关系；
- manifest 以及每个文件的名称、shape、dtype、bytes；
- 训练前和训练后对同一权重的实际数据快照。

判定规则：

- 冻结权重可以继续存在于 canonical RAM 或导出集合中；这不自动构成失败；
- 冻结权重不在导出集合中，也不自动证明它训练前后未变；
- 必须按名称、shape、dtype、元素数量对齐前后快照；
- **实际快照缺席时，不得输出 `frozen_weights_unchanged=PASS`；**
- 只有观察到冻结权重前后相同、目标可训练上游权重按参考结果更新、且图/内存证据显示无冻结参数梯度和
  optimizer state，才可交给训练 Host 验证继续判定。

训练 Host 应至少使用：

```text
x → upstream(trainable) → target(frozen) → loss
```

只在目标算子后放可训练层，可能只证明 forward 输出足以更新下游层，不能证明梯度穿过目标算子并更新上游层。

## 5. 交接格式

冻结任务的实现交接至少包含：

```text
freezing_capability=AVAILABLE|MISSING|NOT_RUN
freezing_capability_evidence=<file:line list>
weight_freezing=<AVAILABLE|MISSING|NOT_RUN|NOT_REQUESTED>
canonical_ram_observed=<yes|no|unknown>
mutable_update_path=<present|absent|unknown>
training_graph_dump=<path or absent>
training_memory_dump=<path or absent>
export_manifest=<path or absent>
weight_snapshot_before=<path or absent>
weight_snapshot_after=<path or absent>
frozen_weights_unchanged=<PASS|FAIL|NOT_VERIFIED>
upstream_trainable_update=<PASS|FAIL|NOT_VERIFIED>
next_owner=hs-verify-op-host training|user
```

没有真实快照、图/内存证据或导出清单时，使用 `NOT_VERIFIED`，不能用文字推断代替证据。
