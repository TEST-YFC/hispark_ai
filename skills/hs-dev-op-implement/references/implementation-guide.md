# 实现指南：逐层代码模板（①–⑦）

> 进入 step4 后**必须**对照本指南逐层实现——不得凭记忆/直觉写代码。路径相对 mindspore-lite 仓库根目录。每层“做/补/复用/不适用”取决于 `docs/decision.md` 的逐层裁决；本指南只给需要实现或修复时的模板与要点。

## 目录

- [① Schema](#-schema)
- [② Parser](#-parser)
- [③ 参数 + Populate](#-参数--populate)
- [④ Infer](#-infer)
- [⑤ Kernel (C 实现)](#-kernel-c-实现)
- [⑥ OpCoder](#-opcoder)
- [⑦ 量化器支持列表检查](#-量化器支持列表检查)
- [CMakeLists — 无需手动更新](#cmakelists--无需手动更新)
- [代码风格](#代码风格)

按层顺序推进。每节要点都已与实际代码核对。INT8 OpCoder 另见 `references/int8-coder-conventions.md`；融合 pass 见 `references/optimizer-fusion-template.md`。

---

### ① Schema

激活子类型和复用已有 primitive 的算子**跳过**。

> **注意：新 PrimitiveType 要改的不止 2 个文件。** 在本集成仓库里一个全新 `PrimitiveType` 必须同步 **6 处**，缺一就编译/转换失败：
>
> | # | 文件 | 改什么 | 漏了的报错 |
> |---|------|--------|-----------|
> | 1 | `src/common/ops/ops_def.cc` | `OP_TYPE(Xxx)` + `OP_SCHEMA_DEF/OP_ATTR` | schema 无该算子 |
> | 2 | `schema/ops.fbs` | **不要手改——生成产物**（见下） | 手改被覆盖 |
> | 3 | `nnacl_c/op_base.h` 的 `enum PrimType` | 追加到**标准段末尾** `PrimType_Xxx = N`（N = 标准段当前最大值 +1），并把 `PrimType_MAX` 改为 `PrimType_Xxx + 1`（务必看下方 ⚠️ 两区段说明） | `'PrimType_Xxx' undeclared`；**或编译通过但 converter 一启动就 SIGSEGV** |
> | 4 | `src/common/ops/primitive/xxx.{h,cc}` | 新建 `ops::Xxx` 原型类 + `kPrimXxx`（见 ①′） | `'Xxx' in namespace 'ops' does not name a type` |
> | 5 | `src/common/ops/ops_func_declare.h` | `#include` + `FUNC_MSOP2SCHEMAOP_DECLARE(Xxx)`（见 ①″） | `MSOp2SchemaOp` 未声明 |
> | 6 | `src/common/ops/ops_utils.cc` | `REG_MINDSPORE_OPERATOR(Xxx)`（见 ①‴） | **编译过、转换静默失败**：`can not find MSOpsRegistry for op: Xxx` → 节点丢失 → `old_nodes is empty` → 算子被列为 `UNSUPPORTED OP` |

> **第 6 处最易漏。** 漏掉 ①‴ 不会有任何编译错误——parser 也照常 `parse op:Xxx`，但 ANF→MetaGraphT 导出时按 op 名在 `MSOpsRegistry` 里查不到 creator，节点被**静默丢弃**。单算子模型因此整图变空，报 `old_nodes is empty`，最终把你的算子打印成 `UNSUPPORTED OP`——极易误判成"parser 没写好"。①″ 只是**声明** `MSOp2SchemaOp`，①‴ 才把它**注册进运行时表**，两者缺一不可。

**`src/common/ops/ops_def.cc`（唯一真值来源）:** union 末尾加 `OP_TYPE(Xxx)`，表定义区加属性表：
```cpp
OP_TYPE(Xxx)                 // OP_TYPE_DEF_BEGIN/END 块内，追加到末尾

OP_SCHEMA_DEF(Xxx)
OP_ATTR(axis, long)          // 注意：标量用 long；向量用 [long]——须与 ops::Xxx 的 getter 返回类型一致
OP_SCHEMA_DEF_END(Xxx)
```

- **`schema/ops.fbs` 由 `ops_def.cc` 自动生成**：构建时 `schema_gen` 读 `OP_SCHEMA_DEF` 宏重写 `ops.fbs`，手改会被下次构建覆盖——**只改 `ops_def.cc`**。（要立刻看到更新可手跑 `build/tools/schema_gen/schema_gen --exportPath=mindspore-lite/schema/`，但通常交给构建。）
- **`OP_ATTR` 元数必须匹配属性真实形态。** `OP_ATTR(axis, long)`（标量）→ `schema_op->axis` 是 `int64_t`；`[long]`（向量）→ `std::vector<int64_t>`。它必须与 `ops::Xxx::get_axis()` 返回类型一致，否则 `cannot convert 'std::vector<long>' to 'int64_t'`。**查 ONNX/TFLite 规格确认属性是单值还是列表**（Hardmax 的 `axis` 是单个 int → `long` + 标量 getter）。

两条硬约束：

- **只能追加到 union 末尾。** 位置决定二进制枚举值（`PrimitiveType_Xxx`），插入会移动后续算子枚举值、破坏既有模型兼容性。`op_base.h` 的 `PrimType_Xxx` 数值应紧接当前最大值 +1。

> ⚠️ **`op_base.h` 的 `enum PrimType` 分两段，别放错。标准段**：`PrimType_NONE=0` … 递增到当前最大算子，后接 `PrimType_MIN`/`PrimType_MAX` 边界。**inner 段**：`PrimType_Inner_*` 从 `10000` 起，位置在 `PrimType_MAX` 之后。新算子接**标准段**末尾（当前最大值+1，如 `LogicalXor=222` → `Hardmax=223`），并把 `PrimType_MAX` 改成 `PrimType_Xxx+1`。**绝不能追加到 `PrimType_Inner_*`（10000+）后面**——kernel 注册表是定长数组 `g_kernelCreatorRegistry[PrimType_MAX][16]`（`nnacl_c/kernel.c`），`REG_KERNEL_CREATOR` 按枚举值做下标，放 10000+ 会越界写穿内存 → converter 启动即无日志 SIGSEGV。
- **`Fusion` 后缀不是通用约定。** 只用于融合/优化变体（`Conv2DFusion`、`AddFusion`…）；多数算子（`Abs`、`Hardmax`…）直接用算子名。

#### ①′ `ops::Xxx` C++ 原型类（新 PrimitiveType 必做，**禁止改 `mindspore/` 子模块**）

parser 会 `std::make_unique<ops::Xxx>()`，必须存在 `mindspore::ops::Xxx`（`BaseOperator` 子类）。

- **正常框架里它由 `mindspore/` 子模块的 YAML + `gen_ops.py` 自动生成**（`auto_generate/gen_lite_ops.*`、`lite_ops.h`）。**但 `mindspore/` 是 pinned 子模块，禁止修改**：手改其 auto_generate 会被重新生成覆盖、且污染子模块。
- **正确做法：在 lite 本地 `src/common/ops/primitive/xxx.{h,cc}` 手写**，模板照抄 `primitive/activation.{h,cc}`：

**`xxx.h`** —— 类 + lite-only `kPrimXxx`：
```cpp
#include <memory>
#include "mindapi/base/types.h"
#include "mindapi/base/macros.h"   // GVAR_DEF
#include "ops/base_operator.h"
#include "ir/primitive.h"          // PrimitivePtr
namespace mindspore {
namespace ops {
constexpr auto kNameXxx = "Xxx";
class OPS_API Xxx : public BaseOperator {
 public:
  MIND_API_BASE_MEMBER(Xxx);
  Xxx() : BaseOperator(kNameXxx) {}
  void set_axis(int64_t axis);          // 类型须与 OP_ATTR 一致（标量）
  int64_t get_axis() const;
};
}  // namespace ops
namespace prim {
// 全新算子在 mindspore/ 里没有 kPrimXxx，lite_ops.h 又不能改，故在此声明（GVAR_DEF 是 header-safe inline）。
GVAR_DEF(PrimitivePtr, kPrimXxx, std::make_shared<Primitive>("Xxx"));
}  // namespace prim
}  // namespace mindspore
```

**`xxx.cc`** —— set/get + 注册 infer（照抄 `activation.cc`）：
```cpp
#include "src/common/ops/primitive/xxx.h"
#include "abstract/ops/op_infer.h"
#include "abstract/ops/primitive_infer_map.h"
#include "mindapi/ir/value.h"
#include "mindapi/helper.h"
#include "ops/primitive_c.h"
#include "utils/check_convert_utils.h"
namespace mindspore {
namespace ops {
MIND_API_OPERATOR_IMPL(Xxx, BaseOperator);
void Xxx::set_axis(int64_t axis) { (void)this->AddAttr("axis", api::MakeValue(axis)); }
int64_t Xxx::get_axis() const { return GetValue<int64_t>(this->GetAttr("axis")); }
class XxxInfer : public abstract::OpInferBase {
  BaseShapePtr InferShape(const PrimitivePtr &, const std::vector<AbstractBasePtr> &a) const override {
    return a[0]->GetShape();   // Hardmax/Softmax 类：输出形状=输入
  }
  TypePtr InferType(const PrimitivePtr &, const std::vector<AbstractBasePtr> &a) const override {
    return a[0]->GetType();
  }
};
REGISTER_PRIMITIVE_OP_INFER_IMPL(Xxx, prim::kPrimXxx, XxxInfer, false);
}  // namespace ops
}  // namespace mindspore
```

- `primitive/*.cc` 由 `mslite_primitive_mid`（仅 `MSLITE_ENABLE_CONVERTER`）用 `file(GLOB)` 自动收录，无需改 CMakeLists。
- `kPrimXxx` 消费者：本文件 `REGISTER_PRIMITIVE_OP_INFER_IMPL` + ⑦ 量化器 `support_int8_ops_.emplace(prim::kPrimXxx)`——量化器需 `#include "src/common/ops/primitive/xxx.h"`（其余 prim 来自 `lite_ops.h`，你的新 prim 只在这里）。

#### ①″ 在 `ops_func_declare.h` 注册（否则 `ops_def.cc` 的 PRIMITIVE_WRITEABLE 路径编不过）

`ops_def.cc` 在 `PRIMITIVE_WRITEABLE` 模式为每个算子生成 `MSOp2SchemaOp(const ops::Xxx*)`（ANF→schema flatbuffer）。两处登记，都在 `#ifdef PRIMITIVE_WRITEABLE` 块内：
```cpp
#include "src/common/ops/primitive/xxx.h"   // 与其它 primitive/*.h 并列
FUNC_MSOP2SCHEMAOP_DECLARE(Xxx)             // 与其它 FUNC_MSOP2SCHEMAOP_DECLARE(...) 并列
```
（`schema_gen` 走 `GEN_SCHEMA_DEF` 模式，这些 include 被 `#ifdef PRIMITIVE_WRITEABLE` 挡掉，schema_gen 不受影响。）

#### ①‴ 在 `ops_utils.cc` 注册运行时 creator（否则转换静默失败，**最易漏**）

①″ 只是声明 `MSOp2SchemaOp(const ops::Xxx*)`；要让 ANF 图导出成 `MetaGraphT` flatbuffer 时真正用上它，**必须**把它注册进 `MSOpsRegistry`。导出路径 `anf_utils.cc::GetPrimitiveT()` 按 **primitive 名**（即 `kNameXxx`）在该表里查 creator：查不到就 `MS_LOG(WARNING) << "can not find MSOpsRegistry for op: Xxx"`、返回 null，节点被丢弃。

在 `src/common/ops/ops_utils.cc` 末尾那串 `REG_MINDSPORE_OPERATOR(...)` 列表里加一行（建议放在 schema 邻近算子旁，如 `LogSoftmax` 后）：
```cpp
REG_MINDSPORE_OPERATOR(Xxx)   // 展开为 PrimitiveCreator<mindspore::ops::Xxx>，注册进 MSOpsRegistry（按名 → creator）
```
- 该宏在 `ops_utils.h`，`#ifdef PRIMITIVE_WRITEABLE` 块内；列表是**手工维护**的，不会自动收录你的新 op。
- 注册键是 `#OP`（大小写/下划线在查表时被 `tolower` + 去 `_` 归一），所以 `REG_MINDSPORE_OPERATOR(Xxx)` 的 `Xxx` 必须与 `ops::Xxx` 类名、`kNameXxx`、parser `ops::Xxx` 三者一致。
- **自检命令**：`grep -n "REG_MINDSPORE_OPERATOR(Xxx)" src/common/ops/ops_utils.cc`——必须命中 1 次。

> 现象 → 根因速记：parser 日志有 `parse op:Xxx`，却又 `Unsupported primitive type in Create: Xxx` + `can not find MSOpsRegistry for op: Xxx` + `old_nodes is empty` + `UNSUPPORTED OP LIST: Xxx` ⟹ 漏了 ①‴。**不是 parser 的问题。**

---

### ② Parser

#### 标准路径 — 新 PrimitiveType

**ONNX** (`tools/converter/parser/onnx/onnx_xxx_parser.cc`):
```cpp
#include "src/common/ops/primitive/xxx.h"  // 新 PrimitiveType 必需：ops::Xxx 手写在 ①′，不在 gen_lite_ops.h（复用已有算子/激活子类型免）

ops::PrimitiveCPtr OnnxXxxParser::Parse(
    const onnx::GraphProto &onnx_graph, const onnx::NodeProto &onnx_node) {
  auto prim = std::make_unique<ops::Xxx>();   // 若为融合变体则是 ops::XxxFusion
  for (const auto &attr : onnx_node.attribute()) {
    if (attr.name() == "some_attr") { prim->set_some_attr(attr.i()); }
  }
  return prim->GetPrim();
}
OnnxNodeRegistrar g_onnxXxxParser("OnnxOpName", new OnnxXxxParser());
```

**一个 parser 类可注册多个 ONNX 算子名**——当多个算子共享同一套属性/输出语义时，复用同一个 parser，按 `onnx_node.op_type()` 内部分流即可。例如 `OnnxReduceParser` 同时注册 `ReduceMean`/`ReduceMax`/`ReduceMin`/`ReduceSum`/`ReduceL2`…，`OnnxConvParser` 注册 `Conv`/`ConvRelu`。新增同族算子时优先扩展已有 parser，而非新建。

#### 复用已有 PrimitiveType 时：parser 的 `ops::Xxx` include 先查真实定义位置

模板里 `#include "src/common/ops/primitive/xxx.h"` 只对**新建分支**成立。复用分支的 `ops::Xxx` 是已有类，定义位置不固定，**写 include 前先 grep**（漏写/写错的报错是 `'Xxx' in namespace 'ops' does not name a type` / `is not a member of 'ops'`）：

```bash
grep -rln "class OPS_API Xxx " ../mindspore/mindspore/ops/op_def/auto_generate/gen_lite_ops.h \
  ../mindspore/mindspore/ops/infer/ src/common/ops/primitive/ 2>/dev/null
```

- 命中 `auto_generate/gen_lite_ops.h`（子模块自动生成，多数已有算子在此）→ include 它；
- 命中 `mindspore/ops/infer/xxx.h` 或本地 `primitive/xxx.h` → include 命中的那个。

include 路径的具体写法（前缀、相对层级）**照抄同目录已有 parser 对同一头文件的既有写法**，不要自创——同一个头在不同目录下的合法写法不同。

**TFLite** (`tools/converter/parser/tflite/tflite_xxx_parser.cc`):
```cpp
TfliteNodeRegister g_tfliteXxxParser(tflite::BuiltinOperator_XXX, new TfliteXxxParser());
```

如果 ONNX 输入顺序与框架期望不同，在 `tools/converter/parser/onnx/onnx_inputs_adjust.cc` 中添加修正。

#### 激活子类型路径

对于激活函数，parser 必须返回带有正确 `ActivationType` 的 `ops::Activation`。返回独立的 op 类（`ops::HSwish`、`ops::LeakyRelu` 等）会导致 MetaGraph 序列化时**静默丢弃**，因为没有匹配的 `PrimitiveType`。

```cpp
// 正确写法：
auto prim = std::make_unique<ops::Activation>();
prim->set_activation_type(mindspore::ActivationType::HSWISH);
return prim->GetPrim();
```

---

### ③ 参数 + Populate

激活子类型**跳过**（使用 `ActivationParameter` 和 `activation_populate.cc`）。

#### 参数结构体

**`src/litert/kernel/cpu/nnacl_c/xxx_parameter.h`:**
```c
#ifndef MINDSPORE_NNACL_XXX_PARAMETER_H_
#define MINDSPORE_NNACL_XXX_PARAMETER_H_
#include "nnacl_c/op_parameter.h"

typedef struct XxxParameter {
  OpParameter op_parameter_;  // 必须是第一个字段——运行时将 OpParameter* 转换为 XxxParameter*
  int some_attr_;
} XxxParameter;
#endif
```

> **一个新 PrimitiveType 必须有自己的 `XxxParameter`，即使字段与某个相近算子（如 Softmax）当前完全相同，也不要复用它的结构体。** Parameter 贯穿 populate→infer→kernel→opcoder→serializer 五层，并参与 micro codegen 的结构体序列化（serializer 的 `CodeStruct`/`CodeBaseStruct` 按**类型名**生成 C 结构体）。复用会造成跨算子类型耦合：任一算子的 Parameter 日后演进就破坏另一个，且生成代码里出现语义错误的结构名。新建 `xxx_parameter.h` 是一次性成本；复用则要在发现后整轮替换五层的全部引用（populate 的 `reinterpret_cast`、infer/kernel 的强转、coder 的成员类型、serializer 的重载与 include），代价远高。

#### Populate

**`src/common/ops/populate/xxx_populate.cc`:**
```cpp
#include "src/common/ops/populate/populate_register.h"
#include "nnacl_c/xxx_parameter.h"
#include "nnacl_c/memory/mem_utils.h"  // NNACLMemMalloc / NNACLMemFree

using mindspore::schema::PrimitiveType_Xxx;  // 必需：REG_POPULATE 用到，不会从 schema 自动带入

namespace mindspore {
namespace lite {
OpParameter *PopulateXxxParameter(const void *prim) {
  auto *primitive = static_cast<const schema::Primitive *>(prim);
  auto *attr = primitive->value_as_Xxx();
  if (attr == nullptr) {
    MS_LOG(ERROR) << "value is nullptr";
    return nullptr;
  }

  // 用 NNACLMemMalloc（注册的分配器抽象），不要用裸 malloc
  auto *param = reinterpret_cast<XxxParameter *>(NNACLMemMalloc(sizeof(XxxParameter)));
  if (param == nullptr) {
    MS_LOG(ERROR) << "malloc XxxParameter failed.";
    return nullptr;
  }
  (void)memset(param, 0, sizeof(XxxParameter));
  param->op_parameter_.type_ = primitive->value_type();
  param->some_attr_ = attr->some_attr();
  return reinterpret_cast<OpParameter *>(param);
}
REG_POPULATE(PrimitiveType_Xxx, PopulateXxxParameter, SCHEMA_CUR)
}  // namespace lite
}  // namespace mindspore
```

要点（与实际代码核对过）：
- 命名空间是 **`mindspore::lite`**，不是 `mindspore::kernel::registry`。
- 用 **`NNACLMemMalloc` / `NNACLMemFree`**（`nnacl_c/memory/mem_utils.h`），不要用裸 `malloc`/`free`；后续校验失败时先 `NNACLMemFree(param)` 再返回 `nullptr`。
- `SCHEMA_CUR = 0` 是当前 schema 版本（`SCHEMA_V0 = 1` 是遗留版本，新算子不用）。
- **严禁把 populate 塞进 `custom_populate.cc` 按字符串名分发**（Custom 捷径，见 SKILL.md 红线 1）。

---

### ④ Infer

激活子类型大多**跳过**（共享 `PrimType_Activation`，统一用 `REG_INFER(Activation, PrimType_Activation, CommonInferShape)`）。**例外：** `LeakyRelu`、`PReLU` 是独立 PrimitiveType，各自有 infer 注册（`PrimType_LeakyRelu` 用 `CommonInferShape`、`PrimType_PReLUFusion` 用 `PReluInferShape`）——若做这两个，infer 不能省。

**`src/litert/kernel/cpu/nnacl_c/infer/xxx_infer.c`:**
```c
#include "nnacl_c/infer/infer_register.h"
#include "nnacl_c/infer/common_infer.h"
#include "nnacl_c/tensor_c_utils.h"   // CheckAugment* 校验宏
#include "nnacl_c/xxx_parameter.h"

int XxxInferShape(const TensorC *const *inputs, size_t inputs_size,
                  TensorC **outputs, size_t outputs_size,
                  OpParameter *parameter) {
  // 1) 先做输入/输出/参数数量与非空校验（几乎每个 infer 都以此开头）
  int check = CheckAugmentWithMinSize(inputs, inputs_size, outputs, outputs_size, parameter, 1, 1);
  if (check != NNACL_OK) return check;

  // 2) 传播 dtype/format
  SetDataTypeFormat(outputs[0], inputs[0]);
  // 3) 输入形状未知（动态 shape）时早退
  if (!InferFlag(inputs, inputs_size)) return NNACL_INFER_INVALID;

  // 3.5) rank 上界闸门（下游有定长 [DIMENSION_xD] 数组的 kernel/coder 时必加）：
  //      infer 是权威上界闸门，超界在此显式报错——不在此拒绝，则 5D 模型 infer 放行、
  //      到 kernel 填定长数组时才越界。守卫常量与下游数组/kernel/coder 取同一个 DIMENSION_xD。
  if ((int)inputs[0]->shape_size_ > DIMENSION_4D) return NNACL_ERR;

  // 4) 计算输出维度
  XxxParameter *param = (XxxParameter *)parameter;
  int out_shape[] = { inputs[0]->shape_[0], /* ... */ };
  // 5) 写回输出形状（直通可用 SetShapeTensor(outputs[0], inputs[0])）
  SetShapeArray(outputs[0], out_shape, sizeof(out_shape) / sizeof(int));
  return NNACL_OK;
}
REG_INFER(Xxx, PrimType_Xxx, XxxInferShape)
```

要点（与实际代码核对过）：
- **开头用 `CheckAugment*` 校验宏**（`tensor_c_utils.c`）：`CheckAugmentNullSize`（精确输入/输出数）、`CheckAugmentWithMinSize`（最小数，允许更多）。几乎所有 infer 都以此起手，跳过会在形状非法时直接崩。
- **rank 上界闸门**：下游 kernel/coder 用定长 `[DIMENSION_xD]` 数组承载 shape 时，infer 必须在此显式拒绝 `shape_size_ > 上限`。**即使下游 kernel 自己也有守卫**，infer 仍要设这道闸——它是 rank 传播的第一道边界，缺它则超界 rank 流到 kernel 才暴露（实证 Hardmax：infer 用 `SetShapeTensor` 无守卫，5D 模型放行到 fp32 kernel 才越界）。直通算子（`SetShapeTensor(out,in)`）尤其容易漏——同形传播不“碰”维度，但下游数组仍会越界。守卫常量与下游所有层使用同一个 `DIMENSION_xD`，并按 `code-quality-gate.md` 的算子专项门禁复核。
- 返回码用 `NNACL_OK` / `NNACL_INFER_INVALID`（不是 `RET_OK`）。
- `REG_INFER(op, type, func)` 第一个参数是构造注册函数名的 C token（`Reg##op##Infer`），不是"昵称"——取唯一标识即可，习惯与 PrimType 短名一致。
- 顺序：校验 → 传播 dtype/format → 动态 shape 早退 → 算维度 → 写回。此函数在转换时（codegen 的 `CreateOpCoders`）和运行时都会执行——保持无副作用。

---

### ⑤ Kernel (C 实现)

先判定本算子的 **dtype 路径**，再选目录。`fp32/` 只表示浮点计算路径，不是"默认实现目录"。

| 算子 dtype 语义 | 需要的 kernel/coder 路径 | 不要做 |
|---|---|---|
| **浮点输入算子**（源规格输入/输出是 float，`riscv_int8` 由量化器生成） | float 路径 + 量化 int8 路径；float kernel 供普通执行和全量化校准使用 | 不要省略 float kernel |
| **原生整型/索引/离散 dtype 算子**（规格本身就是 `int8/uint8/int32/int64/bool` 等，如 `ConvInteger`、`Cast`、索引类） | 按规格逐 dtype 注册。纯整型计算放 `nnacl_c/int8/`（int8/uint8 数值计算）或 `nnacl_c/base/`（dtype-generic、搬运、索引/控制类）；生命周期/注册仍可放 `nnacl_c/kernel/` 或既有 `base/` LiteKernel 体系 | **不要**因为"INT8 豁免"而跳过 `int8/uint8` 注册；也不要伪造 `nnacl_c/fp32/xxx_fp32.c` / `opcoders/nnacl/fp32/xxx_fp32_coder.cc` |
| **首输入 condition/index 的跨 dtype 算子** | 一个固定派发键 kernel/coder，内部按数据张量 dtype 分支；通常放 `base/` 或既有体系内扩展 | 不要注册死的 `kNumberTypeInt8` 平行 kernel |

#### float kernel — 浮点输入/需量化的算子必需

对浮点输入算子，float kernel 是**必需的**，即使最终只部署 `riscv_int8`——`full_quant_quantizer.cc` 在校准期间运行完整的 float 模型来收集输入/输出数据分布。缺少 float kernel 会导致全量化失败。

float 纯计算函数放在 **`nnacl_c/fp32/xxx_fp32.c`**（无注册，被下面任一路径调用，也被 ⑥ opcoder `Collect()` 进 MCU 工程）。在此之上，float 在 CPU 上有**两条并存的注册路径**——跟随 `docs/decision.md` 选定的同族参考算子，它用哪条你就用哪条：

| 路径 | 注册宏 / 文件 | 形态 | 占比 |
|---|---|---|---|
| **A. C `KernelBase`**（nnacl 多数算子） | `REG_KERNEL_CREATOR(PrimType_Xxx, kNumberTypeFloat32, CreateXxx)`，写在 **`nnacl_c/kernel/xxx.c`** | C 结构体 + vtable（`Prepare`/`Compute`/`Resize`/`InferShape`，定义见 `nnacl_c/kernel.h`） | ~294，主流 |
| **B. C++ `LiteKernel`** | `REG_KERNEL(kCPU, kNumberTypeFloat32, PrimitiveType_Xxx, LiteKernelCreator<XxxCPUKernel>)`，写在 **`src/litert/kernel/cpu/fp32/xxx_fp32.cc`** | C++ 类（`Prepare()`/`Run()`/`ReSize()`） | ~50 |

```c
// 路径 A：nnacl_c/kernel/xxx.c
KernelBase *CreateXxx(OpParameter *param, int data_type) {
  XxxStruct *xxx = (XxxStruct *)NNACLMemMalloc(sizeof(XxxStruct));
  NNACL_MALLOC_CHECK_NULL_RETURN_NULL(xxx);
  memset(xxx, 0, sizeof(XxxStruct));        // ← 把 vtable 全置 0，未显式赋值的函数指针就是 NULL
  xxx->base_.Prepare = DefaultPrepare1In1Out;
  xxx->base_.Resize  = XxxResize;
  xxx->base_.Compute = XxxCompute;
  xxx->base_.Release = DefaultRelease;      // 必填！无额外 buffer 用 DefaultRelease（no-op）；有 buffer 写自己的 XxxRelease 释放它
  return (KernelBase *)xxx;
}
REG_KERNEL_CREATOR(PrimType_Xxx, kNumberTypeFloat32, CreateXxx)
```

> **漏设 `base_.Release` 会段错误。** `nnacl_kernel.cc` 在销毁 kernel 时**无条件**调用 `kernel_->Release(kernel_)`——`memset` 后它是 NULL，于是解引用空函数指针崩溃。**四个 vtable 指针（Prepare/Resize/Compute/Release）一个都不能少**：结构体无额外 buffer 用 `DefaultRelease`（参考 `nnacl_c/kernel/pooling.c` / `pad.c`），有 buffer 写自己的 `XxxRelease`（参考 `nnacl_c/kernel/softmax.c` 的 `SoftmaxRelease`）。这个崩溃**不会在 hs-verify-op-host 的 micro benchmark 里出现**（它跑 opcoder 生成的 C，从不调用 `Release`），只在**全量化校准的 pre-inference**（`Model::Build` fork 子进程 build+run+销毁）暴露：日志是 `encounter an unknown error...` + `PreBuild or PreInference failed`，子进程被信号杀死。凡见此报错，先查新 kernel 的 vtable 是否设全（尤其 `Release`）。
```cpp
// 路径 B：src/litert/kernel/cpu/fp32/xxx_fp32.cc
REG_KERNEL(kCPU, kNumberTypeFloat32, PrimitiveType_Xxx, LiteKernelCreator<XxxCPUKernel>)
```

注意（与实际代码核对过）：
- 调度顺序是 **先 C++ LiteKernel（路径 B），无则回退 C `KernelBase`（路径 A）**；但只注册其中一条即可工作，两条都注册（如 Arithmetic）也合法。
- 路径 A 的 `KernelBase` creator 在 **`nnacl_c/kernel/xxx.c`**，不是 `nnacl_c/fp32/`——后者只放纯计算函数。Pooling 等大量算子只走路径 A（无 `fp32/pooling_fp32.cc`）。
- 全量化校准（`full_quant_quantizer.cc` 跑 fp32 `Predict()`）会自动用上述任一可用路径。
- **`nnacl_c/{fp32,int8,fp16,infer,base}/` 下新建 .h 一律带 `extern "C"` 守卫**（声明区包入 `#ifdef __cplusplus extern "C" { #endif … #ifdef __cplusplus } #endif`，同目录任一既有头都是样例）。这些头被 C++ 侧（LiteKernel/coder/serializer）include，缺守卫**编译不报错、链接期才报 undefined reference**，烧一轮完整构建才暴露；`quick_check.sh` 已对此做秒级 lint，但正确写法是起笔就带上。

#### 原生 dtype kernel — 原生整型/离散算子

原生 dtype 算子不是"float 算子被量化后运行"。它们的输入/输出 dtype 是规格语义本身，所以：

- **按规格逐 dtype 注册派发键**：`kNumberTypeInt8`、`kNumberTypeUInt8`、`kNumberTypeInt32`、`kNumberTypeBool` 等都是不同入口。能力清单里出现的 dtype 必须能走到对应 kernel。
- **按真实计算语义放目录**：int8/uint8 数值计算（如整数卷积、整数查表、整数比较）优先放 `nnacl_c/int8/xxx_int8.c` 或同族既有 int8 文件；跨 dtype 搬运/shape/index/control 逻辑放 `nnacl_c/base/` 或既有 `nnacl_c/kernel/` 体系内。`nnacl_c/kernel/xxx.c` 只负责 `KernelBase` 生命周期和注册，不代表计算 dtype。
- **不要补量化器列表**，除非它同时也是浮点输入算子的量化 int8 路径。原生 dtype 的 `int8` 不需要 `full_quant_quantizer` 给它制造 qparams。
- **不要把原生整型-only 计算放进 `fp32/`**。`xxx_fp32.c`、`xxx_fp32_coder.cc` 这类命名会误导后续维护者和 weak model：目录名声称浮点路径，实际却处理整型输入/输出。

如果一个算子既支持 float 输入，又支持原生整型输入（少见但可能），两条路径分别落目录：float 计算在 `fp32/`，原生整型计算在 `int8/` 或 `base/`，不要用一个 `fp32` 文件兼容所有 dtype。

#### 量化 int8 kernel — 浮点输入算子的 INT8 部署路径

涉及两个不同文件，别混淆：

- **`nnacl_c/int8/xxx_int8.c`** — 纯 int8 计算函数。无需注册；既被运行时 int8 kernel 调用，也被 ⑥ opcoder 通过 `Collect()` 复制进 MCU 工程。
- **`src/litert/kernel/cpu/int8/xxx_int8.cc`** — 运行时 int8 LiteKernel（C++ 类，含 `Prepare()` + `Run()`）。它在全量化的 **bias_correction** 阶段被 converter 执行，从运行时 `Tensor::quant_params()` 读取 scale/zp。（这与 `nnacl_c` 的 `TensorC` 不同——`TensorC` 没有量化字段，MCU 上的量化参数由 ⑥ opcoder 烘焙为编译时常量。两条路径独立。）

运行时 int8 kernel **需要注册**，通过 `REG_KERNEL(kCPU, kNumberTypeInt8, PrimitiveType_Xxx, Creator)`。Creator 有两种通用形态：

| 形态 | 何时用 | 写法 |
|---|---|---|
| 模板 creator（多数算子） | 一个 PrimitiveType 对应一个独立 kernel 类 | `LiteKernelCreator<XxxInt8CPUKernel>` |
| 自定义 creator 函数 | 一个 creator 服务多个 PrimitiveType，或要在子类型/变体间选择 | 如 `CpuActivationInt8KernelCreator`（按 ActivationType）、`CpuArithmeticInt8KernelCreator`（比较类）、`CpuConvInt8KernelCreator`（卷积变体） |

新增**子类型**（落到自定义 creator 这一类）时，要在该 creator——或它构造的 kernel `Prepare()`——里补上对应分支；漏掉会在 bias_correction 阶段报错中断（例如按 mode 分发的 kernel 会打印 `[<op>_int8.cc:NNN] Prepare] <Op> unsupported mode: N`）。这类多路复用文件还要在顶部与其它 `using` 并列导入用到的 schema 枚举（枚举不会自动导入），例如 `using mindspore::schema::ReduceMode_ReduceL1;`。

`Prepare()` 的通用职责：从 `in_tensors_[0]->quant_params()` / `out_tensors_[0]->quant_params()` 取 scale/zp，校验非空，按需用 `QuantizeMultiplier` 预计算定点乘数（中间量类型/公式须与 runtime int8 kernel 一致，见 `references/int8-coder-conventions.md`）。

运行时 int8 LiteKernel（`src/litert/kernel/cpu/int8/xxx_int8.{h,cc}`）分两部分对待——**工程骨架算子无关、逐字照抄；数值部分从本算子规格推导，绝不从参考算子拷贝**：

- **参考算子按结构族选**（同 fp32「参考算子选型」原则），不存在"通用照抄某一个算子"：选 body 最小、语义最近的那个做骨架——序关系/选择类（argmax/topk/hardmax）看 `topk_int8`/`argminmax_int8`，带重量化的逐元素二元看 `add_int8`/`mul_int8`，归约看 `reduce_int8`，激活子类型走 activation creator。**抄它的结构（注册、生命周期、读 qparams 的方式），不抄它的数值。** 反面教材：拿 `softmax_int8`（带 `in_quant_args_` 输入重量化 + `QuantizeMultiplier` 定点乘数 + `exp/sum` scratch buffer）当通用骨架，会把本算子根本不需要的字段一并拖进来——序关系算子 int8 **只读 output 的 scale/zp**、写固定量化 0/1，与输入 scale 无关。先按本算子规格确定"int8 到底需要哪些 qparams、哪些数值运算"，再决定抄谁、抄哪几行。
- **算子无关的骨架（这部分照抄）**：

```cpp
// xxx_int8.h
#include "src/litert/lite_kernel.h"            // 基类头；不是 .../kernel/cpu/base/lite_kernel.h（不存在）
class XxxInt8CPUKernel : public LiteKernel { ... };

// xxx_int8.cc
#include "src/litert/kernel_registry.h"        // REG_KERNEL / KernelRegistrar
using mindspore::lite::KernelRegistrar;        // REG_KERNEL 展开后用到
using mindspore::schema::PrimitiveType_Xxx;
namespace mindspore {
namespace kernel {                             // 运行时 kernel 用 mindspore::kernel（populate 用 ::lite）
auto in = reinterpret_cast<int8_t *>(in_tensors_.at(0)->MutableData());  // 取数据用 MutableData()，无 data_c()
}  // namespace kernel
}  // namespace mindspore
REG_KERNEL(kCPU, kNumberTypeInt8, PrimitiveType_Xxx, LiteKernelCreator<XxxInt8CPUKernel>)
```

- **生命周期契约（最易丢，丢了是隐性 bug）**：`Prepare()` 必须建立 `Run()` 需要的**全部**派生态（shape、`n_dim_`、axis 归一化、qparams），并以 **`return ReSize();`** 收尾。把 shape 派生态只放在 `ReSize()` 是错的——converter 的 **bias_correction** 子流程**不保证 `ReSize()` 先于首个 `Run()`**，会 `n_dim_=0` 致 int8 全路转换 FAIL（实证 Hardmax）。本仓 53 个有 `Prepare()` 的 int8 kernel 中 42 个以此收尾，是框架契约不是个别算子的风格。`ReSize()` 负责按当前 shape 重算派生态，含定长数组（`input_shape_[DIMENSION_xD]` 类成员）填充循环前的 `> DIMENSION_xD` 守卫（rank 判据 ② 见下）。
- **`nnacl_c/**/*.c` 是 C 文件，强转写 `(int32_t)(x)`，不能用 `static_cast<>`。** 只有 `.cc`（LiteKernel、opcoder）是 C++。
- **防御性代码两条，抄模板时最容易丢（实证：Hardmax 两处全丢，预检/构建/验证三道闸全放行——它们只测合法输入包络）：**
  1. **每个**向固定长数组（`input_shape_[DIMENSION_xD]` 类成员）填充的循环前都要守卫：`ReSize()`/`Prepare()`/`InitParam`/nnacl `Resize` 里 `for i<n_dim` 直写数组前，必须先 `MS_CHECK_TRUE_RET(in_dims <= DIMENSION_xD, RET_ERROR)`（C kernel 用显式 `if (n_dim > DIMENSION_xD) return NNACL_ERR;`）。这是 SKILL.md rank 不变量判据 ②：**infer 与每个写数组的层都要守，且取同一个 `DIMENSION_xD`**——不要把 infer 设宽（如 `DIMENSION_8D`）而数组开窄（`DIMENSION_4D/5D`），那是实证反例 A；也不要"各层常量都对上了"就以为安全——infer 用 `SetShapeTensor` 无守卫 + nnacl kernel 填充前无守卫 = 反例 B，常量全 4D 仍越界。`quick_check.sh` rank advisory (2)/(3) 会秒级拦这两处，命中即修。
  2. 所有 `Init*/Resize` 等校验函数的返回值必须传播（`ret != NNACL_OK` 即 return）；丢弃返回值 = 校验失败后拿 memset 残值静默算错，比崩溃更糟。

#### ⑤′ 归约/选择类内核：初值取首元素，禁用域边界常量作哨兵

适用于**沿轴做选择或归约**的算子：`ArgMax`/`ArgMin`/`ReduceMax`/`ReduceMin`/`TopK`/`Hardmax` 等——凡内核里出现"求最大/最小值及其下标"的循环都算。

**`max_val`/`min_val` 及其 `idx` 必须用该轴首元素初始化、`idx` 从 0 起；禁止用类型/量化域的边界常量（`INT8_MIN`、`output_activation_min_`、`-FLT_MAX` 之类）当哨兵。**

理由：浮点域里 `-FLT_MAX`/`-INFINITY` 可作哨兵，因为真实数据取不到；但**整型/量化域不存在 −∞，域下限（如 `INT8_MIN = -128`）是合法数据值**。当某轴元素全部恰好等于该下限——典型如全零浮点输入经非对称量化后整列都落到 zp/−128——`x > sentinel` 恒为 false，归约**塌缩**：无元素被选中（如 Hardmax 输出全零）或 argmax 返回 -1。fp32 实现常因哨兵取 −∞ 而"看起来正确"，掩盖同构的 int8 缺陷，极具欺骗性——**fp32 全过不能证明选择逻辑对**。

```c
// 反例（int8 选择类内核）：用量化下限作哨兵 → 整列等于下限时无人当选
int8_t max_val = quant->output_activation_min_;   // = -128（合法数据值，不是 −∞）
int max_idx = -1;
for (int j = 0; j < axis_size; j++) { if (in[base + j * inner] > max_val) { ... } }

// 正确：首元素起步，平局取首个（符合 ONNX argmax/Hardmax 语义）
int8_t max_val = in[base];
int max_idx = 0;
for (int j = 1; j < axis_size; j++) { if (in[base + j * inner] > max_val) { ... } }
```

> hs-verify-op-host 的 `all-zeros` / `single-element-axis` 用例正是为暴露这类塌缩而设。它们 FAIL 几乎总是初值契约被违反，**不是**“量化精度极限”——按 Host skill 的失败分流保留原始日志并回流实现。

#### ⑤″ 首输入是 condition/index 的算子（条件选择、按索引取数类）：int8 **不要**单独注册

"int8 LiteKernel 注册在 `kNumberTypeInt8` 键"只对**首输入即数据张量**的算子成立。若算子**首输入是固定 dtype 的非数据张量**（条件选择类的 condition 恒为 `bool`、gather 类的 indices 为 `int`），**运行时与 codegen 都按 `inputs[0]->data_type()` 选 kernel**——运行时见 `src/litert/scheduler.cc::GetFirstFp32Fp16OrInt8Type`（返回首个输入的 dtype），codegen 见 `session.cc`。后果：

1. **整个算子只有一个 kernel 键**（首输入的固定 dtype，如 `bool`），不分 fp32/int8。
2. **注册在 `kNumberTypeInt8` 键上的运行时 kernel 永不被选中 = 死代码**，别写它。
3. **注册在固定键（bool）上的那个 kernel 必须自己按数据张量 `in_[1]->data_type_` 分支**，处理 fp32 / int8 / fp16。**int8 分支按 ⑤‴ 模板做逐输入重量化**——重量化在各方 qparams 相同时自动退化为恒等拷贝，永远正确；直接字节拷贝只在量化器把各输入与输出绑到同一 scale+zp 时才对，**而这不能假设、必须从生成代码核实**，否则输入/输出 scale 不同的场景可能以接近阈值的结果假绿。
4. **致命陷阱**：若 bool 键 kernel 对 int8 数据仍按 fp32 计算（把 int8 缓冲当 `float*` 写），每元素写 4 字节进 1 字节缓冲 → 堆越界，表现为全量化 **bias_correction** 阶段 `malloc(): corrupted top size` / `sysmalloc: Assertion failed`（**大张量崩、小张量侥幸过**，fp32/x86 路正常，ASAN 下因分配向上取整反而不崩——极难定位）。
5. **放置**：这个唯一的运行时 kernel 放数据搬运类常规位置（C++ `LiteKernel` 放 `base/`，C `KernelBase` 放 `nnacl_c/kernel/`），按 bool 键注册一处；别散落多个按 dtype 注册的 kernel（其余都是死的）。
6. **在已有 kernel 上加 int8 分支 = 先做全执行路径审计**。打开该 kernel 的 `Run()`/`Compute()`，列出**每一条**写输出的路径：按 dtype 的 switch 各分支、scalar/单元素条件的**快路**（`MoveData`/`memcpy` 整块搬运）、in-place 与 early-return 分支。逐条裁决「int8 数据可达吗？可达则经过重量化吗？」——只给主 switch 加 int8 case 而放过旧快路，quantized 数据从快路漏过去就是绕开重量化的字节拷贝，且这类路径常由单元素用例触发、其余弦恒为 1.0，行为验证无法暴露（详见 hs-verify-op-host 用例设计的单元素告诫）。快路对 int8 不安全时，把 int8 显式从快路条件中排除、并入重量化分支。
7. **扩展既有 kernel 必须留在它既有的体系内，禁止另起平行 kernel。** 运行时 kernel 查找顺序：`REG_KERNEL` creator 注册表**优先**、nnacl 注册表兜底（`src/litert/kernel_registry.cc::GetLiteKernel`——creator 命中即不再查 nnacl）。给已由 `NNACL_KERNEL(...)` 承载的算子按同键再加一个 `REG_KERNEL` C++ kernel，新 kernel 会**整体劫持**该算子全部执行（首输入派发下，一个 bool 键覆盖所有数据 dtype），既有 nnacl kernel——连同其已验证的广播物化、快路、fp16 逻辑——全部沦为死代码；反向注册在 int8 键则永不被选中（第 2 条）。两个方向都是缺陷。正确路径按既有体系二选一：
   - **nnacl `KernelBase` 体系**（`nnacl_c/kernel/xxx.c` + `src/litert/kernel/cpu/nnacl/nnacl_xxx.cc` 的 C++ shim）需要量化参数时：给 `XxxStruct` 加**扁平** quant 字段（⑤‴ 结构约束），在 shim 里从 `in_tensors_[i]->quant_params()` 填充——shim 是 `LiteKernel` 子类拿得到 `lite::Tensor`，而纯 C 的 `TensorC` 没有 qparams；int8 计算分支加在 `xxx.c` 内（调 ⑤‴ 的 `XxxInt8` 函数）。
   - **C++ `LiteKernel` 体系**：直接在既有 kernel 的 `Run()` 加数据 dtype 分支。

   另：**给 struct 加字段、或引用任何 struct 字段之前，先 Read 它的定义**。按记忆引用不存在的字段（臆造 `where->quant_params_` 之类）→ 编译失败 → 误判"这条路走不通" → 换体系另写平行 kernel，是已实证的连锁错误链；正解从来是回到定义补字段，不是换体系。

#### ⑤‴ 多数据输入 / 搬运·选择类算子的 int8 重量化【模板】

**适用范围（先对号入座）：**

| 算子形态 | 是否用本模板 |
|---|---|
| 搬运/选择类——值从某个输入**原样**进输出（条件选择、Concat、Slice/Gather/Tile…） | **用**。这正是模板形态 |
| 逐元素二元算术（Add/Mul/Sub…） | 原则相同（按来源 qparams 入、按输出 qparams 出），但**同族若已有现成 runtime int8 kernel（如 `arithmetic`/`add_int8`），按 §2 镜像现有 kernel，不要套此模板**——它们常用更高精度的定点乘数方案 |
| 单数据输入算子（激活、Softmax/Hardmax、归约…） | **不归本节**，用 §1–§8 的单输入约定 |

**为什么必须重量化（一句话记住）：** 量化器给每个输入张量和输出张量**各自独立**分配 `(scale, zp)`；**重量化在各方 qparams 恰好相同时自动退化为恒等拷贝，所以默认写重量化永远正确**；直接整型字节拷贝只在各方 qparams 相同时才对——是**有条件正确**，禁止默认采用（§9）。

**模板**（以三输入条件选择为载体；**按你算子的形态增减**：N 个数据输入就 N 组 `scale/zp` 字段（或数组），无条件输入就去掉 `condition`——不变的是**每个写入输出的值，按其来源张量的 qparams 重量化到输出 qparams**）。**两条结构性约束先记住：**

- **重量化用模板的 `float ratio + lrintf`，不要替换成定点乘数方案。** `QuantizeMultiplierSmallerThanOne` 等定点接口面向卷积/算术类的预算乘数路径，对 `ratio = 1.0`（输入输出 scale 相同，搬运/选择类最常见的情形）产出的不是恒等变换——结果是系统性 ~2× 偏差，且只在部分用例上暴露。float-ratio 写法对任意比值正确、qparams 相同时自动退化为拷贝，MCU 上每元素一次 `lrintf` 的成本对搬运类算子可接受。
- **量化参数结构体保持扁平**（只含 `float`/`int32_t` 标量字段，不嵌套子结构体）。serializer 的 `CodeBaseStruct` 对标量字段直接工作；嵌套结构体则要求为每个子结构体额外补 `nnacl_stream_utils.{h,cc}` 的 `operator<<` 重载（声明/定义/include 又是三处），徒增接线面与编译失败回合。N 个输入就平铺 N 组 `inN_scale_/inN_zp_` 字段。

**1) `nnacl_c/int8/xxx_int8.h`** —— 签名必须携带各输入与输出的量化参数：

```c
#include "nnacl_c/op_base.h"

#ifdef __cplusplus
extern "C" {       // 必带：本头会被 C++ 侧（runtime kernel/coder）include，缺守卫 = 链接期 undefined reference
#endif

typedef struct XxxInt8QuantParams {
  float in1_scale_;  int32_t in1_zp_;
  float in2_scale_;  int32_t in2_zp_;
  float out_scale_;  int32_t out_zp_;
} XxxInt8QuantParams;

void XxxInt8(const bool *condition, const int8_t *in1, const int8_t *in2, int8_t *output, int num,
             const XxxInt8QuantParams *quant);

#ifdef __cplusplus
}
#endif
```

**2) `nnacl_c/int8/xxx_int8.c`**：

```c
#include "nnacl_c/int8/xxx_int8.h"
#include <math.h>

void XxxInt8(const bool *condition, const int8_t *in1, const int8_t *in2, int8_t *output, int num,
             const XxxInt8QuantParams *quant) {
  float ratio1 = quant->in1_scale_ / quant->out_scale_;
  float ratio2 = quant->in2_scale_ / quant->out_scale_;
  for (int i = 0; i < num; i++) {
    int32_t v = condition[i] ? (int32_t)lrintf((float)(in1[i] - quant->in1_zp_) * ratio1)
                             : (int32_t)lrintf((float)(in2[i] - quant->in2_zp_) * ratio2);
    v += quant->out_zp_;
    output[i] = (int8_t)MSMAX(MSMIN(v, INT8_MAX), INT8_MIN);
  }
}
```

**3) runtime kernel 与 ⑥ opcoder 调用同一个 `XxxInt8`** —— 这是 §2「bit-for-bit 一致」最省力也最不易错的实现方式：

- **runtime int8 路径**（bias_correction 阶段执行）：从各张量 `quant_params().front()` 读 scale/zp 填 `XxxInt8QuantParams`，调 `XxxInt8`。**不得走恒等拷贝捷径**（runtime 拷贝、coder 重量化 → bias_correction 与 MCU 发散）；**也不得在 runtime kernel 里另写一份重量化循环**——与 nnacl `.c` 重复的内联副本日后必然漂移，"调同一个函数"正是 bit-for-bit 一致的实现手段。同理，不要加"qparams 为空就退回字节拷贝"的兜底分支：全量化通路里 qparams 必然存在，为空属异常，按 §5 报带算子名的错误并返回。
- **opcoder `Prepare()`**：从 `input_tensors_` / `output_tensor_` 的 `quant_params()` 读取填同一结构体；逐个 `MS_CHECK_TRUE_MSG(!q.empty(), ...)` 校验非空（错误消息带算子名前缀，§5）。
- **opcoder `DoCode()`**：
  ```cpp
  Collect(context, {"nnacl_c/int8/xxx_int8.h"}, {"xxx_int8.c"});
  NNaclInt8Serializer code;
  code.CodeStruct("xxx_quant_params", quant_);   // 需在 nnacl_int8_serializer.{h,cc} 加该结构体的 CodeStruct 重载（见 ⑥ int8 节，.h 声明/.cc 定义/include 三处缺一不可）
  code.CodeFunction("XxxInt8", condition_tensor, in1_tensor, in2_tensor, output_tensor_, num, "&xxx_quant_params");
  context->AppendCode(code.str());
  ```

**自检（写完必查两条）：**
- int8 函数签名里**没有任何 scale/zp 参数 = 字节拷贝 = 默认是 bug**（§9）。
- 生成代码里输入侧 `DoQuantizeFp32ToInt8(scale_a, zp_a)` 与输出侧 `DoDequantizeInt8ToFp32(scale_b, zp_b)` 的 qparams 不同、而中间只有拷贝 → 失配实锤，必须改用本模板。

> 唯一豁免：该算子规格**强制**输入与输出同 qparams **且**从生成代码确认转换器确实落实（输入/输出 scale 实际相等）。注意源框架的量化 trait（如 TFLite `SameOperandsAndResultsScale`）约束的是**源框架自家 converter/runtime**，本仓库的 `full_quant_quantizer` 按各张量自身值域独立分配 qparams、并不落实它——**trait 本身不构成豁免依据**，只有生成代码里实测 scale 相等才算。豁免须在函数注释写明依据；拿不准就用本模板——qparams 相同时 `ratio=1`，重量化自动退化为拷贝，不会错。

#### ⑤⁗ 广播类 kernel：先复用既有设施，确需手写按标准公式

适用于任何**多输入且各输入形状允许不同**（numpy 式广播）的算子——含给存量广播 kernel 补缺口的情形。

**先排除一条诱人的歧路——图层 pass 插广播节点。** 往 `anf_transform.cc` 的 pass 列表插 `BroadcastTo`/`Reshape` 节点、把广播"前移"到图里，看似免改 kernel，实则有两个硬前置，**全部查实之前不得选该方案**：(a) 被插入的算子 × 它要承载的 dtype（广播 condition 时是 **bool**）必须在 micro opcoders 注册表里有 coder——`BroadcastTo(bool)`/`Reshape(bool)` 通常没有：converter 能过、codegen 即挂，报错位置远离根因；(b) `InitFusions` 列表对**所有模型全局生效**，回归面是全仓所有算子，不是本算子。实证事故：为条件选择类补广播，两次走图层 pass 方案，全部用例 ERR 后整体回滚，净烧 3 轮构建 + 2 轮验证。本节优先级 1/2（kernel/coder 内部处理）才是默认路径。

**优先级 1 — 复用，不手写。** 仓库已有两类现成广播设施：把各输入物化成输出形状再走同形路径的 `nnacl_c/base/broadcast_to.{h,c}`（运行时 kernel 常用此法）；以及逐元素算术族里既有的按 stride 索引实现。先看参考算子怎么做，能调用就调用——每多手写一份索引逻辑，就多一份要做 ⑤″ 全路径审计的对象。

**两条既有方案，按"是否需要 scratch"二选一（读参考算子时先认出它用哪条；arithmetic/Sub = 物化，Where = stride 索引）：**

| 方案 | 广播逻辑放哪 | scratch | MCU codegen | 适用 |
|---|---|---|---|---|
| 物化 / tile | kernel 编排层 + coder：把广播输入 tile 成输出形状，再走**等长核** | 输出大小 ×N | coder 用 `allocator_->Malloc(..., kWorkspace)` 申请——**这是编译期静态工作区规划，不是堆 malloc**；别误判"MCU 不能 malloc 所以不能物化"（实证：本人一度据此错误排除物化方案） | 元素操作贵、buffer 可复用 |
| stride 索引（零分配） | 独立 broadcast 计算函数按 stride 取数，不物化 | 零 | coder 把 stride 在转换期算成编译期常量结构体（`CodeStruct` 发数据）+ 调用 | 廉价逐元素 + 想免分配（如 Where 的条件选择） |

**计算函数保持广播无感、按 dtype 分文件。** 无论哪条方案，逐元素核（`SubInt8`、`WhereWithTripleInputsInt8`）都是**等长、零广播逻辑**，int8 落 `int8/`、fp32 落 `fp32/`。广播要么在编排层物化后喂等长核（方案 1），要么写成**另一个广播变体函数、与等长核同放该 dtype 文件**（方案 2，如 `where_int8.c` 同时有 `WhereWithTripleInputsInt8` 等长核 + `BroadcastWhereInt8` 广播核——`sub_int8.c` 同放 `SubInt8` + NEON 变体即此惯例）。**一个 dtype 出现多个 int8 计算函数时，hs-verify-op-host 的 `INT8_KERNEL_SYMBOL` 要列全所有符号**（列表形，否则发射另一变体的用例被误判 `INT8_NOT_GENUINE`）。

**stride 数学只写一份、runtime 与 coder 共用同一函数。** 把 stride 计算 + 索引 inline 助手放 `base/`（如 `base/broadcast_where.{h,c}` 的 `ComputeBroadcastWhereStrides` + `static inline BroadcastWhereOffsets`）：runtime kernel 在 Resize/Compute 调它，coder 在转换期调**同一个 C 函数**把结果烘焙成常量结构体。stride 公式只存在一处 → 一次 numpy oracle 验证即可，杜绝"runtime/coder/fp32/int8 各抄一遍各错一遍"（弱会话实证：coder 内联 stride 连错 3 轮）。新建的 `base/*.c` 用 `NNACL_OK/NNACL_ERR` 须 `#include "nnacl_c/errorcode.h"`（op_base.h 不含；quick_check 秒级抓）。

**优先级 2 — 确需手写**（典型：codegen 侧要把形状烘焙成编译期常量）**按此公式，两处经典错误都标在注释里：**

```c
// 各输入 shape 先左侧补 1 对齐到输出 ndim（PadShape）。
// stride 自右向左：stride[d] = 右侧各维之积——乘 shape[d+1]，不是 shape[d]！
// （错位成 shape[d] 是高频 bug：编译过、同形用例全过，广播用例余弦掉到 0.0x–0.5）
stride[ndim - 1] = 1;
for (int d = ndim - 2; d >= 0; d--) stride[d] = stride[d + 1] * shape[d + 1];

// 输出平铺下标 i → 某输入的下标：逐维取坐标，该输入在此维为 1 则取 0（广播）
int idx = 0, rem = i;
for (int d = 0; d < ndim; d++) {
  int coord = rem / out_stride[d]; rem %= out_stride[d];
  if (in_shape[d] > 1) idx += coord * in_stride[d];
}
```

**快路守卫必须对每个输入逐一成立。** 加"同形/标量走快路"的优化时，条件是**全部**输入各自满足 `num == out_num || num == 1`；写成"任一输入是标量"之类的存在性条件，会把另一个仍需非平凡广播的输入也放进快路 → 越界读/取错数。混合形态（一个输入标量 + 另一个输入非平凡广播同时出现）正是弱守卫的盲区，hs-verify-op-host 的广播用例必须包含它。

**禁止用 `i % num` 近似广播索引**：模运算只对"最外维广播 + 其余维同形"碰巧正确，中间维广播（`[2,1,4]` 对 `[2,3,4]`）取错数。要么物化（优先级 1），要么完整 stride 映射（优先级 2），没有第三条路。

---

### ⑥ OpCoder

此层在 `converter_lite` 内运行，生成随 MCU 固件一起发布的 C 源代码。⑤ 中的 kernel C 文件通过此处的 `Collect()` 调用被复制到生成的项目中。

先选 **coder 目录**，不要把 `fp32/` 当默认位置：

| coder 形态 | 目录 | 注册键 |
|---|---|---|
| float 输入/float 计算路径 | `tools/converter/micro/coder/opcoders/nnacl/fp32/` | `kNumberTypeFloat32` |
| 量化 int8 路径（float 算子经量化器变成 int8） | `tools/converter/micro/coder/opcoders/nnacl/int8/` | `kNumberTypeInt8`，并与 runtime int8 kernel/qparams 完全对齐 |
| 原生 int8/uint8 数值算子（规格本身就是整型输入） | 优先 `opcoders/nnacl/int8/`，或沿用同族既有目录；按 `kNumberTypeInt8` / `kNumberTypeUInt8` 等逐键注册 | 不需要量化器 genuine 符号，但必须发射真实整型计算函数 |
| 多原生 dtype / 首输入非数据张量 / 控制、索引、搬运类 | `tools/converter/micro/coder/opcoders/base/` | 固定派发键或多 dtype 注册，内部按数据张量 dtype 分支 |

判断标准是"生成代码处理的真实 dtype 和派发键"，不是"有没有量化器"。原生整型-only 算子若放进 `opcoders/nnacl/fp32/`，后续模型会误判它是 float 路径，并在 decision3/step3 继续写出「fp32 做 / int8 跳过」这类错误总结。

#### float coder

**`tools/converter/micro/coder/opcoders/nnacl/fp32/xxx_fp32_coder.h`:**
```cpp
// 根基类是 OperatorCoder（不存在 NNaclFP32Coder 这个类）
class XxxFP32Coder final : public OperatorCoder {
 public:
  // 构造函数签名照抄如下五参形态（透传给基类即可）——不要凭记忆增删参数（如臆造 schema_version）
  XxxFP32Coder(const std::vector<Tensor *> &in_tensors, const std::vector<Tensor *> &out_tensors,
               const LiteGraph::Node *node, size_t node_index, Target target)
      : OperatorCoder(in_tensors, out_tensors, node, node_index, target) {}
  ~XxxFP32Coder() override = default;

  int Prepare(CoderContext *const context) override;
  int DoCode(CoderContext *const context) override;
};
```

基类选择要跟随 `docs/decision.md` 选定的同族参考算子，**不要一律写 `OperatorCoder`**：简单算子（Activation、Power、Concat、Slice…，约 100 个）直接继承 `OperatorCoder`；但很多算子族有**类别中间基类**，fp32/int8 coder 共享其打包逻辑——
`Conv2DBaseCoder`、`MatMulFP32BaseCoder` / `MatMulBaseInt8Coder`、`SoftmaxBaseCoder`、`ReduceBaseCoder`、`ResizeBaseCoder`、`TileBaseCoder`、`FullConnectionBaseCoder` 等。若参考算子继承的是某个 `*BaseCoder`，照抄它，而非 `OperatorCoder`。

**`tools/converter/micro/coder/opcoders/nnacl/fp32/xxx_fp32_coder.cc`:**
```cpp
int XxxFP32Coder::DoCode(CoderContext *const context) {
  // Collect(ctx, headers, cFiles={}, asmFiles={})：第 3、4 个参数可选
  Collect(context,
    {"nnacl_c/xxx_parameter.h", "nnacl_c/fp32/xxx_fp32.h"},  // 需要嵌入的头文件
    {"xxx_fp32.c"});                                          // 需要嵌入的 .c 源文件
                                                              // 第 4 个参数 asmFiles 一般省略

  NNaclFp32Serializer code;
  // codesize（见 ⑥′）：若 nnacl 函数只需某个标量字段（如 axis），直接传标量，别传整个 parameter 指针
  code.CodeFunction("XxxCompute",
                    input_tensor_, output_tensor_,
                    reinterpret_cast<XxxParameter *>(parameter_));
  context->AppendCode(code.str());
  return RET_OK;
}
REG_OPERATOR_CODER(kAllTargets, kNumberTypeFloat32,
                   PrimitiveType_Xxx, CPUOpCoderCreator<XxxFP32Coder>)
```

复杂 coder 可把 `Collect()` 抽到独立的 `CollectFiles()` 里再由 `DoCode()` 调用（见 `activation_fp32_coder.cc`），简单算子直接在 `DoCode()` 开头调用即可。

**`DoCode` 只发"数据 + 调用"，禁止内联生成算法。** `DoCode` 的职责是发 `CodeStruct`（参数/量化结构体）与 `CodeFunction`（对 nnacl_c 函数的调用）；**不要用 `code << "for (...)"` 内联生成计算循环**——计算逻辑（含每种形状模式、广播形态、特殊条件形态）一律落在 nnacl_c 函数里，⑤ runtime 与 ⑥ codegen 调**同一个函数**（int8 见 ⑤‴ §3，fp32 同理）。内联副本三宗罪：绕开 runtime kernel 已验证的逻辑；bias_correction（跑 runtime kernel）与 MCU（跑生成代码）行为发散；修编译错误重写 coder 时最容易被整段删掉（实证：特殊形态分支在一次修错重写中被静默丢弃，编译变绿，拖到 hs-verify-op-host 才 FAIL）。nnacl 函数尚不支持某形态 → **扩展该函数签名**（加 mode/inner_size/stride 参数，同形等常规形态传退化值），kernel 与 coder 同步受益——而不是把该形态写成 coder 里的私有循环或 C++ kernel 里的私有副本。
张量地址：`CodeFunction` 直接传 `Tensor *` 即可——serializer 对指针参数自动解析运行时地址（`serializer.h::GenCode` → `MemoryAllocator::GetRuntimeAddr`）；需要显式字符串地址时用 `allocator_->GetRuntimeAddr(tensor)`。不要凭记忆调形似的工具函数（`coder_utils.h` 里的 `GetTensorAddr` 是 4 参自由函数，按 1 参成员调用直接编译失败）。

> **目录约定：跨 dtype 的 coder 放 `opcoders/base/`，不要放 `opcoders/nnacl/fp32/`。** 若一个 coder **单次注册即服务多种数据 dtype**（典型：dispatch key 落在非数据输入上——如条件选择类首输入是 bool，coder 内部按数据张量 dtype 分 fp32/int8 生成代码），它属于"跨 dtype"coder，应命名 `xxx_base_coder.{h,cc}` 放 **`opcoders/base/`**（与运行时多 dtype kernel 放 `src/litert/kernel/cpu/base/` 一致）。参考 `reshape_base_coder`、`stack_base_coder`、`strided_slice_base_coder`、`softmax_base_coder`——它们都在 `base/` 内按 data_type 分支。放进 `fp32/` 但实际处理 int8，是命名与目录不符的缺陷。
>
> **命名空间差异（从 `nnacl/` 参考算子仿写 `base/` coder 时最常踩）：** `opcoders/base/` 的 coder 在 `mindspore::lite::micro` 命名空间，而 serializer 类（`NNaclFp32Serializer` / `NNaclInt8Serializer`）定义在 `mindspore::lite::micro::nnacl`——base/ coder 用它们必须在文件顶部加 `using mindspore::lite::micro::nnacl::NNaclFp32Serializer;`（int8 同理），否则报 `'NNaclFp32Serializer' was not declared in this scope`。`opcoders/nnacl/` 下的 coder 本身就在 nnacl 命名空间内、无此问题，所以参考算子文件里看不到这行 using。另注意工程以 `-Werror` 编译：未使用的局部变量直接编译失败，写完自查一遍。

对于激活子类型，在 `opcoders/nnacl/fp32/activation_fp32_coder.cc` 的 `AllocationOperator()` switch（按 `ActivationParameter::type_`）中添加 `case ActivationType_XXX:` 分支，而非新建 `REG_OPERATOR_CODER`。该 switch 用 `break` 收尾，新增分支记得补 `break`。

#### ⑥′ codegen 效率【每个新 coder 必查】：MCU 上 codesize 很贵，生成的每行 C 都烧进 flash

> **这是 OpCoder 层最高频、也最易被忽视的浪费点——opcoder 的职责不止"能跑通"，还要让发出的 C 尽量小。** 生成代码随固件烧进有限 flash，每多一个结构体定义、每多一段尾零都实打实占空间。下面两条务必落实（完成检查清单里有对应自查项）：

1. **能直接传标量就别 `CodeStruct` 整个 parameter 结构体。** 看你要调用的 nnacl 函数签名：如果它形参是 `int axis`（标量）而非 `XxxParameter *`，就直接把解析好的整数传给 `CodeFunction`，**不要** `code.CodeStruct("xxx_parameter", *param_)` 再传 `"xxx_parameter.axis_"`。后者会在生成代码里多塞一个完整结构体定义，只为取一个字段。
   ```cpp
   // 反例（浪费）：为取一个 axis 发了整个 HardmaxParameter 结构体
   code.CodeStruct("hardmax_parameter", *hardmax_param_);
   code.CodeFunction("Hardmax", input_tensor_, output_tensor_, "hardmax_parameter.axis_", n_dim_, "input_shape");
   // 推荐：直接传标量（axis 已在 Prepare/DoCode 里解析成非负）
   int axis = hardmax_param_->axis_ < 0 ? hardmax_param_->axis_ + n_dim_ : hardmax_param_->axis_;
   code.CodeFunction("Hardmax", input_tensor_, output_tensor_, axis, n_dim_, "input_shape");
   ```
   这样还**省掉**对应的 `NNaclFp32Serializer`/`NNaclInt8Serializer` 里的 `CodeStruct(XxxParameter)` 重载——不需要就别加。

2. **shape 数组只发 `n_dim_` 个元素，别发固定的 `DIMENSION_5D`。** 内核只读 `input_shape[0..n_dim-1]`；发满 5 个会带尾零（2D 张量生成 `{N,C,0,0,0}`）。
   ```cpp
   code.CodeStruct("input_shape", input_shape_, n_dim_);   // 不是 DIMENSION_5D
   ```
   （`input_shape_[DIMENSION_xD]` 这个**缓冲区**和它填充前的 `in_dims <= DIMENSION_xD` 这个**守卫**用同一个 `DIMENSION_xD`——本项目上限通常 4D。**不要照抄参考算子里 infer 比数组宽的差异**：那种 infer `DIMENSION_8D` / 数组 `DIMENSION_5D` 的不一致正是实证反例 A，会被 `quick_check.sh` rank advisory (1) 拦下；coder 的 `Prepare/DoCode` 若也填定长数组，填充前同样要守卫，与 infer/kernel 取同一常量。）

#### int8 coder

**仅当 nnacl 函数确实接收某个结构体指针时**，才在 `opcoders/serializers/nnacl_serializer/nnacl_int8_serializer.{h,cc}` 加 `CodeStruct()` 重载——**`.h` 加声明、`.cc` 加定义、并 `#include` 该结构体头文件，三处缺一不可**。重载内部调用 `CodeBaseStruct(...)`（不要在 coder 里直接调用 `CodeBaseStruct`）。量化参数结构（`XxxQuantArg`）通常需要这个重载；纯标量属性（axis 等）按 ⑥′ 直接传、不要重载。`CodeBaseStruct` 列出的字段顺序必须与 C 结构体定义完全一致。参见 `relux_int8_coder.cc` / `leaky_relu_int8_coder.cc`。

对于激活子类型，在 `opcoders/nnacl/int8/activation_int8_coder.cc` 的工厂函数 `CreateActivationInt8Coder()` 中为新的 `ActivationType_XXX` 添加分支。注意该 switch 是 **case-return 形态**（每个 case 直接 `return CPUOpCoderCreator<XxxInt8Coder>(...)`），没有 `break`、也不会穿透；`default` 返回 `nullptr`。照已有 case 的写法加一行即可。

**写 INT8 coder 之前先阅读 `references/int8-coder-conventions.md`。**
最重要的约定：**int8 coder 必须逐位复刻对应 runtime int8 kernel（`src/litert/kernel/cpu/int8/<op>_int8.cc`）的乘数运算**——相同的中间类型、常量、公式。因为 converter 在 bias_correction 阶段跑的就是该 runtime kernel，MCU 输出要与之对齐。本仓库（如 hswish）乘数用 **`float`** 中间量再传入 `QuantizeMultiplier`（其形参是 `double`，float 在调用处自动提升）；**照抄 kernel 的 float 写法，不要擅自改成 `double`**，否则生成代码与 kernel 不一致、相似度校验会失败。

#### Wrapper

如果需要线程分割或参数打包，在 `coder/wrapper/fp32/` 或 `coder/wrapper/int8/` 中添加 wrapper（`.h`/`.c` 一并 `Collect()` 进生成工程）。大多数算子不需要。

**禁止为 codegen 方便往 runtime 头（`nnacl_c/fp32|int8/xxx.h`）里塞 `static inline` 包装函数**——runtime 头是运行时与 MCU 共用的纯计算接口，codegen 专属的便利函数一律放上述 wrapper 目录（参照 `wrapper/int8/concat_int8_wrapper.{h,c}`）。典型诱因是"结构体含指针字段，`CodeStruct` 不好发"：正解是把参数**扁平化**为标量（⑤‴ 结构性约束）或**扩 nnacl 函数签名**（见 ⑥「DoCode 只发数据 + 调用」节的"扩展该函数签名"），不是加头文件内联包装——内联包装既污染 runtime 接口，又常伴随去 const 的 C 风格 cast 等代码味。

---

### ⑦ 量化器支持列表检查

**文件：** `tools/converter/quantizer/full_quant_quantizer.cc`

- **激活子类型：** 验证 `support_activation_` 包含新的 `ActivationType` 值，且激活内核/OpCoder 已支持该子类型。
- **浮点输入算子的 full int8：** 验证 `support_int8_ops_`（在 `enable_all_ops` 分支下）包含 `prim::kPrimXxx`（融合变体则为 `kPrimXxxFusion`），但只能在 ⑤ int8 runtime、⑥ int8 OpCoder、生成代码依赖、量化参数传递和 int8 精度探针均有证据后添加。
- **per-channel 权重量化：** `per_channel_ops_` 只控制权重量化粒度（per-channel vs per-layer），不是 int8 计算支持列表。某 op 出现在 `per_channel_ops_` 而不在 `support_int8_ops_` 时，结论是「权重量化策略已有，full int8 未开放/未证明」，不是「int8 已覆盖」。

如果 `support_int8_ops_` 缺失且上述证据齐全，添加 `(void)support_int8_ops_.emplace(prim::kPrimXxx);` 到 `enable_all_ops` 块。否则全量化静默跳过该算子，tensor 保持 fp32——而 OpCoder 仅凭 `inputs[0]->data_type()` 选择 fp32/int8 分支（见 `op_coder_builder.cc`），于是选中 fp32 coder。**giveaway：`riscv_quant` 的余弦相似度会恰好打印 `1.0000`**（与 fp32 完全一致）；真正的 INT8 量化应落在 `[0.99, 1.0)`。若添加后出现 `int8_genuine=yes` 但余弦低于阈值，说明 full int8 路径已打开但计算不正确，必须回到 ⑤/⑥ 修实现，禁止归因为“support 列表已修完”。

---

### CMakeLists — 无需手动更新

所有相关目录使用 `file(GLOB)` / `file(GLOB_RECURSE)`，新的 `.cc` / `.c` 文件无需写进 CMakeLists：

- `tools/converter/parser/onnx/` 和 `tflite/`
- `src/common/ops/populate/`
- `nnacl_c/infer/`、`nnacl_c/fp32/`、`nnacl_c/int8/`、`nnacl_c/base/`
- `opcoders/nnacl/fp32/`、`opcoders/nnacl/int8/`、`opcoders/base/`
- `tools/optimizer/fusion/`、`tools/optimizer/graph/`

新文件增量编译即可生效：`build.sh`（含 `-i`）每次都重跑 `cmake` configure（`scripts/build/build_lite.sh`：`-i` 只保留 `build/`、不跳过 configure），`file(GLOB)` 随之重新扫描。`file(GLOB)` 的陈旧只在**绕过 build.sh、直接在 `build/` 里跑 `make`/`ninja`** 时出现——那时需手动重跑 cmake。

---

### 代码风格

本仓算子代码以代码根 `.clang-format` 和本 Skill 的 `references/code-style.md` 为准。两者发生
格式差异时，格式由 `.clang-format` 决定，安全与可维护性规则由 Skill 内置规范决定。完整执行清单见
`references/code-quality-gate.md`。不要使用“固定 2 空格、函数 100 行”这类泛化描述：当前项目门禁要求
函数不超过 50 个非空非注释行、5 个参数和 4 层嵌套，并对修改代码执行仓内 clang-format。
Python 遵循 PEP 8。

**禁止魔数（G.CNS.02）** — 不要使用难以理解的字面量。代码中出现的数值常量必须通过命名常量或枚举表达其含义。例如：
```cpp
// 反例：魔数，读者无法理解 6 的含义
if (input_tensors_.size() == 6) { ... }

// 推荐：通过命名常量或已有宏说明含义
const size_t kSixInputWithBatchAndPadding = 6;
if (input_tensors_.size() == kSixInputWithBatchAndPadding) { ... }

// 更好：复用已有的 nnacl 宏
if (input_tensors_.size() == SIX_TENSOR) { ... }
```
常见豁免：`0`（初始化/偏移）、`1`（单位步长/乘数）、标准索引常量（如 `kInputIndex = 0`、`FIRST_INPUT`、`SECOND_INPUT`）不需要额外命名。

新文件必须使用**当前年份**的 Apache 2.0 版权头。**年份先跑 `date +%Y` 取真实值，禁止凭记忆/凭参考文件的旧年份填**（对"今年"的认知常滞后，照抄参考文件会把旧年份带进新文件）：
```cpp
 * Copyright <date +%Y 的输出> Huawei Technologies Co., Ltd
```

**头文件规范** — 只包含头文件中直接使用的内容。特别注意，不要在 C++ 文件中包含 `nnacl_c/op_base.h`（纯 C 头文件），除非头文件签名中使用了其中的 C-only 类型。将 `.cc` 专用包含（如 `quantize.h` 用于 `QuantizeMultiplier`）从头文件中移出。
