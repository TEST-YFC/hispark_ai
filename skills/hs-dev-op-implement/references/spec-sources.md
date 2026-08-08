# 规格与参考实现取材

decision1 的存在性裁决与语义摘要由 `scripts/fetch_op_spec.py` 给出（scan_op.sh 内部已调）。本文覆盖脚本之外的取材：逐个属性的细节（默认值/取值范围）、上游内核参考实现、全部源不可达时的兜底。

## 两条原则

- **一律按最新 opset 实现（项目裁决）**：opset 间默认值/语义有变时只实现最新版，parser **不做 opset 分支、不拒绝旧 opset 模型**——旧模型按最新语义解析（如 Hardmax：axis 默认 -1 逐轴语义，无视模型声明的 opset）。要求两件事：① parser 加一行策略注释留痕（模板见 SKILL.md step4）；② 差异本身写进属性审计呈现。**禁止为该行为编造技术依据**（如"旧 opset 模型会序列化显式属性值"——ONNX 不序列化等于默认值的属性，此类断言即臆造，见下文证据标准）。仓内个别旧 parser（如 onnx_softmax_parser.cc 的 opset 分支）是历史写法，不作为新算子的范式。
- **deprecated ≠ 可跳过**：规格里仍有就按最新 opset 完整处置。

## 取材优先级：本地 onnx 包 > 本地克隆 > WebFetch > curl/wget > 问用户

**ONNX 属性/输入输出的首选来源是本地安装的 onnx python 包**（hs-verify-op-host 环境必装，权威、完全离线、企业网拦截 WebFetch 时仍可用）——`fetch_op_spec.py` 的语义摘要已内置属性表（名/类型/必需/默认值），通常 scan 输出就够；需要补查时直接：

```bash
python3 -c "from onnx import defs; s=defs.get_schema('<OpName>'); print(s.since_version); \
print({n:(str(a.type),a.required) for n,a in s.attributes.items()})"
```

其次查 `references/` 下可能已克隆的 `onnx/`、`onnxruntime/`、`tensorflow/`、`tflite-micro/`（用前校验：空文件、`404`、HTML 错误页一律当不存在）。**上游内核参考无本地克隆时用 `scripts/fetch_ref_impl.py --op <Op>`**——它按镜像链（jsDelivr → ghproxy 系 → 直连 raw）取材并缓存 `/tmp/ref_impl/`，企业网被墙也能走通；**禁止手工 curl raw.githubusercontent.com 直链或自写内省脚本**（直链被墙必失败，失败后最易滑向凭记忆补）。规格类需求按下表；某框架查无此算子是正常情况，标注即可，不反复重试。

| 需求 | 本地路径（优先） | 脚本/网络回退 |
|---|---|---|
| **ONNX 规格** | **本地 onnx 包（见上，最优先）**；`references/onnx/docs/Operators.md` | `curl -sL "https://onnx.com.cn/onnx/operators/onnx__<OpName>.html" \| grep -oP '(?<=<p>).*?(?=</p>)'` |
| **ONNX 内核参考** | `references/onnxruntime/onnxruntime/core/providers/cpu/<category>/` | `python3 <skill>/scripts/fetch_ref_impl.py --op <Op> --repo onnxruntime` |
| **TFLite 规格 / 内置算子列表** | `references/tensorflow/tensorflow/lite/builtin_ops.h` | `fetch_op_spec.py` 已带镜像链自动回退；语义页 `curl -sL "https://tensorflow.google.cn/mlir/tfl_ops" \| grep -i -A 30 "tfl.<opname>"` |
| **TFLite 内核参考** | `references/tflite-micro/tensorflow/lite/micro/kernels/<op>.cc` | `python3 <skill>/scripts/fetch_ref_impl.py --op <Op> --repo tflite-micro`（运行时参考 `--repo tflite`） |

ONNX heading 格式是 `### <a name="OpName">...</a>`；raw 提取用 `grep -A 80 "^###.*OpName"`（`.*` 跳过中间标签）。

**存在性断言的证据标准**：写"某框架有此算子"前必须实际跑过查证并看到命中；查无命中就记"无此算子"。尤其禁止凭记忆补"废弃于 opset X–Y""是 … 的别名"之类具体却无据的细节——这类听起来精确的断言正是最典型的臆造形态。decision4 呈现时每个框架结论后附依据（命中 `文件:行` 或 `0 命中→无此算子`）；证据格为空的行视同未完成。

## 上游内核参考的读法（写 ⑤ 前）

带着这些问题整理笔记（不抄代码，只记理解）：算法公式、属性如何影响计算、输入输出形状关系、**边界情况（空输入/单元素/全零/标量）**、数据类型约束、中间量精度（float vs double）。

**选优权限分层**：算法核心（循环结构、广播策略、快路设计、边界处置）由参考实现对比表对比后自行裁决最优——能找到比上游更适合 MCU 的简单实现优先，理由写进表；**工程骨架（注册宏、目录归属、量化接口形态、int8 重量化数值方案）由实现指南锁死，不在选优范围**。适配时只抄算法逻辑，不抄工程细节（SIMD/线程池/内存池），内存布局改 `nnacl_c` 风格（`TensorC` + 裸指针 + `NNACLMemMalloc`）。

## 全部源不可达时（唯一合法兜底，禁止编造）

向用户索取：输入（名称/dtype/必需性/广播）、输出（dtype/与输入形状关系）、属性（名称/类型/默认值/范围）、目标框架。有模型文件也可从 `onnx.NodeProto` / TFLite schema 推断。

## 语义摘要中量化 trait 的处理

`SameOperandsAndResultsScale` 之类 trait 描述的是源框架自家 runtime 的约定，**对本仓库不生效**——MSLite 的 `full_quant_quantizer` 给每个张量独立分配 scale/zp。该 trait 不是 int8 跳过重量化的依据；int8 通路一律按实现指南 ⑤‴ 模板逐输入重量化（qparams 恰好相同时自动退化为拷贝，永远正确）。
