# 端到端范例

两个范例分别演示 **decision2** 的两条分支——复用已有 PrimitiveType / 新建 PrimitiveType。教的是**可复用的决策过程**，不是某算子的速查表：拿到任意算子时，按同样的次序走 decision1→decision4，落到对应分支的实现清单。

范例里的算子只是载体；把它换成你手上的算子，每一步问的问题不变。

---

## 范例 A：复用已有 PrimitiveType

**载体：** 一个三输入广播条件选择算子（`output = cond ? x : y`，三输入支持广播）。这类"换了个名字/换了个框架，语义不变"的算子最容易被误当成全新算子从头实现——A 范例就是要避免这一点。

### decision1 查规格

按 SKILL.md decision1 的查阅位置表，分别在 ONNX、TFLite 规格里查该算子：

- 确认它在**哪些框架真实存在**。常见情况：某框架根本没有这个名字，而是用一个**语义等价的已有算子**表达（条件选择在 ONNX 里就是 `Where`）。**某框架查无此名 → 该框架不注册 parser、不为它造用例**（按 decision1 标注"该框架无此算子"），绝不臆造一个该框架并不定义的算子名。
- 摸清同一目标在该框架下可能对应的**多个 builtin**。条件选择在 TFLite 有两个 builtin：非广播版与广播版——同一个上层调用，输入 shape 全相同时框架发前者、有广播时发后者。这层映射关系**由源框架定义**，必须在 decision1 查清，不能仅凭内置名推测。

### decision2 复用 vs 新建 → 判定：复用

套用 decision2 的"完全等价"判据（输入个数/顺序/语义、输出语义、属性集、广播规则全一致）：本算子与已有的广播选择 PrimitiveType（`Where`）三输入、广播、无属性，逐项一致 → **复用，不新建 PrimitiveType**。

### decision4 链路分析（填好的表）

对被复用的 PrimitiveType 跑 decision4 的链路扫描（`scripts/scan_op.sh <算子名> <代码根>` 一条命令产出），得到它现存链路：

| 环节 | 状态 | 说明 |
|------|------|------|
| ① Schema PrimitiveType | 已有 | 复用，不动 |
| ①‴ ANF→schema 导出注册 | 已有 | 复用，不动 |
| ② Parser (ONNX) | 已有 | ONNX 用现成的 `Where` parser |
| ② Parser (TFLite) | **缺失** | 两个 builtin（非广播 + 广播）都要注册 |
| ③ Populate | 已有 | 复用 |
| ④ Infer | 已有 | 复用（已含广播形状推导） |
| ⑤ Kernel float | 已有 | 复用 |
| ⑤ Kernel 量化int8 | **缺失** | 已有 kernel 仅处理 float 数据，缺量化 int8 数据分支 |
| ⑥ OpCoder | **缺失** | 复用型最常见的缺口——旧算子往往只有运行时通路、没有 MCU coder |
| ⑦ 量化器支持列表 | **缺失** | `full_quant_quantizer.cc` 未含该 prim |

**只补缺失的四项：② TFLite parser、⑤ 量化 int8 分支、⑥ OpCoder、⑦ 量化器。** 已有的 ①③④⑤float 一律不重写——把它们重做一遍正是要避免的反模式。

### 实现缺失环节

1. **② TFLite parser——只注册语义真正匹配本 PrimType 的 builtin。** 框架里名字相近的 builtin **不一定语义相同**：条件选择的**非广播版与广播版是两个不同 builtin、对应两个不同 PrimType**（广播版 → 本例复用的广播选择 PrimType；非广播版 → 仓库里另一个非广播 PrimType，是**独立算子**，单独按范例 B 走自己的链路）。本 parser **只注册广播版那个 builtin**、返回所复用的 op 类；非广播版**另起 parser、另映射**，不得图省事塞进同一 parser——语义不同，强行共用会算错。
   > 源框架可能按输入形状择优发不同 builtin（条件选择：同形状发非广播版、需广播才发广播版）。所以"漏注册另一个 builtin 会随机 FAIL"的正解**不是**把它也指向本 parser，而是**两个算子各自实现、各自注册**，再用测试形状把它们分开（见下「验证用例设计」）。

2. **⑤ int8 kernel 分支：** 在已有 kernel 里按数据张量 dtype 增加 int8 分支。**多数据输入算子的 int8 必须逐输入独立重量化**——每个输入张量带各自的 `(scale, zp)`，输出也有自己的，默认互不相同；绝不能假设 x/y 共用一个 scale，也不能逐字节拷贝（等于假设 in==out）。**直接照抄 `implementation-guide.md` ⑤‴ 的完整模板**（带 qparams 的 .h/.c + runtime 与 opcoder 调同一函数），原理见 `int8-coder-conventions.md` §9。

3. **⑥ OpCoder（注册键看首输入 dtype）：** 该算子首输入是 condition（bool），运行时按 bool 派发，因此**只注册一个 coder key**（条件输入的 dtype），coder 内部再按**数据张量**（非首输入）的 dtype 生成 fp32 / int8 代码。不要拆成 fp32+int8 两个 `REG_OPERATOR_CODER`（会撞 key）。

4. **⑦ 量化器：** 在 `full_quant_quantizer.cc` 的 `enable_all_ops` 块 `support_int8_ops_.emplace(prim::kPrim<被复用算子>)`。漏了则 `riscv_quant` 余弦恰好 `1.0000`。

### 验证用例合同（交给 workflow，再路由 hs-verify-op-host）

- **只为该算子真实存在的框架建用例**：若 ONNX 用等价算子表达、TFLite 才有该 builtin，就只写 TFLite 用例，别凭空造 ONNX 用例。
- **用例形状要能逼出目标 builtin。** 源框架按输入形状择优发不同 builtin（条件选择：同形状→非广播版，需广播→广播版）。验证广播版 PrimType 时用例**必须带广播（不同形状）**；同形状用例会被发成非广播 builtin、落到另一个算子的通路上，测的根本不是本算子。非广播版那个算子则用**全同形状**用例单独建项目。两个算子据此各自分流，无需把两个 builtin 混进一个项目凑。
- 必含一条**多输入不同值域**的用例（如 x∈[0.1,6]、y∈[−6,−0.1]）——让两个数据输入得到不同 scale，这是唯一能验出"逐输入重量化是否写对"的用例。

---

## 范例 B：新建 PrimitiveType

**载体：** 一个全新的带属性逐元素算子，在已有 PrimitiveType 里找不到语义等价物。

### decision1 查规格 + decision2 判定：新建

先查清输入/输出/属性/dtype/广播，并做属性审计（每个属性标注支持/默认拒绝/不支持），再套 `decision2-reuse-decision.md` 的“完全等价”判据。无任何已有 PrimitiveType 匹配时裁决为**新建**，并在 `docs/decision.md` 逐层记录实现范围。

### decision4 链路分析（填好的表）

全新算子的链路全缺：

| 环节 | 状态 |
|------|------|
| ① Schema + ①′①″①‴ | 缺失（新建需同步 6 处，见实现指南 ①） |
| ② Parser | 缺失 |
| ③ 参数 + Populate | 缺失 |
| ④ Infer | 缺失 |
| ⑤ Kernel float / 量化int8 / 原生dtype | 缺失（本例是浮点输入算子：做 float + 量化int8） |
| ⑥ OpCoder float / 量化int8 / 原生dtype | 缺失（本例是浮点输入算子：做 float + 量化int8） |
| ⑦ 量化器支持列表 | 缺失 |

### 实现次序（每步指向实现指南对应节）

按 implementation-guide ①→⑦ 顺序逐层，落笔前对照该节模板：

1. **① Schema（最易漏的是 6 处不同步）：** `ops_def.cc` 加 `OP_TYPE`+`OP_SCHEMA_DEF`/`OP_ATTR`；`op_base.h` 的 `PrimType_Xxx` 接**标准段**末尾并 `PrimType_MAX+1`（放错段→启动即 SEGV）；新建 `primitive/xxx.{h,cc}`（①′）；`ops_func_declare.h` 声明（①″）；`ops_utils.cc` 加 `REG_MINDSPORE_OPERATOR`（①‴，漏了编译过但转换静默丢节点）。
2. **② Parser：** ONNX/TFLite 各按需，返回 `ops::Xxx`；属性逐条转发或显式拒绝。
3. **③ 参数 + Populate：** 新建**独立的** `XxxParameter`（即便字段与某算子相同也不复用），`REG_POPULATE`。
4. **④ Infer：** `CheckAugment*` 起手 → 传播 dtype/format → 动态 shape 早退 → 算维度 → 写回，`REG_INFER`。
5. **⑤ Kernel：** 先按 dtype 语义分类；本例是浮点输入算子，所以做 float 纯计算 + 注册（路径 A `KernelBase` 四个 vtable 指针设全，含 `Release`），并按 1c 判定补量化 int8 kernel。若是原生整型-only 算子，不伪造 float/fp32 路径，按规格逐 dtype 注册。
6. **⑥ OpCoder：** 本例做 float + 量化 int8，`Collect()` 列全生成代码引用的头/源；codesize 自查（⑥′）。原生 dtype 算子按实现指南 ⑥ 的目录表选择 `opcoders/nnacl/int8/` 或 `opcoders/base/`。
7. **⑦ 量化器：** `support_int8_ops_.emplace(prim::kPrimXxx)`。

### 验证

算子实现专项 Skill 只冻结 capability checklist 和 implementation contract；随后交回 `hs-workflow-op-development`，由其调用
`hs-verify-op-host` 按算子属性、值域和形状编写并运行用例。细则见 Host skill。

---

两个范例并列：拿到算子先走 decision1→decision2，**判出复用还是新建**，再对照对应范例的链路分析表与实现清单。复用就只补缺口、绝不重写已有层；新建就按 ①→⑦ 全做。
