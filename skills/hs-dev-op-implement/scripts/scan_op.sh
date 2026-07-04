#!/bin/bash
# Copyright 2026 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# scan_op.sh <OpName> [mindspore-lite 代码根目录]
#
# hs-dev-op-implement step1 一键扫描，一条命令产出 decision1 + decision4 的全部查证材料：
#   1) decision1 框架存在性裁决 + 语义摘要（内部调 fetch_op_spec.py）
#   2) decision4 ①–⑦ 链路现状逐环节扫描（0 命中显式标「缺失」，不会被误读成"没输出"）
# 输出即查证证据——据此填写「框架对应关系表」与「链路分析表」，呈现给用户后再实现。
set -u

OP="${1:?用法: scan_op.sh <OpName> [mindspore-lite 代码根目录(含 schema/ops.fbs 的那级)]}"
ROOT="${2:-.}"
DIR="$(cd "$(dirname "$0")" && pwd)"

# 完整输出落盘兜底：调用方用 head/tail 截断管道时（被禁止，但要防），全文仍在此文件。
# 实证教训：tail -60 恰好截掉 decision1 的 ONNX 语义摘要段，模型拿幸存的另一框架同名摘要误判了候选语义。
LOG="/tmp/scan_op_$(printf '%s' "${OP}" | tr -cd 'A-Za-z0-9_').log"
exec > >(tee "${LOG}") 2>&1
echo "[i] 完整输出同步保存: ${LOG} —— 只看到部分输出时（截断/超时）从该文件读全文，禁止凭片段下 decision1/decision2 结论"

echo "############ decision1 框架存在性裁决 + 语义摘要: ${OP} ############"
python3 "${DIR}/fetch_op_spec.py" --op "${OP}" \
  || echo "[!] 存在性 UNREACHABLE → 按 decision1 兜底停下问用户，禁止凭记忆断言存在与否"

echo
echo "############ decision1′ 上游参考 kernel 候选（「参考实现对比表」取材，见 SKILL.md decision1） ############"
# 本地克隆（references/ 下）按文件名命中上游参考 kernel；无克隆的仓用 fetch_ref_impl.py 联网取材。
REFS="${DIR}/../references"
OPK="$(printf '%s' "${OP}" | tr '[:upper:]' '[:lower:]' | tr -d '_')"
BASEK="$(printf '%s' "${OP}" | sed -E 's/V[0-9]+$//' | tr '[:upper:]' '[:lower:]' | tr -d '_')"
MISSING_CLONE=0
for repo in onnxruntime tensorflow tflite-micro; do
  if [ ! -d "${REFS}/${repo}" ]; then
    echo "  ${repo}: (无本地克隆 → 用下方 fetch_ref_impl 命令联网取材)"
    MISSING_CLONE=1
    continue
  fi
  echo "  ${repo}:"
  find "${REFS}/${repo}" \( -path "*/.git" -o -name "*test*" \) -prune -o \
       -type f \( -name "*.cc" -o -name "*.c" -o -name "*.h" \) -print 2>/dev/null \
    | awk -F/ -v a="${OPK}" -v b="${BASEK}" \
        '{f=tolower($NF); gsub(/[_.]/,"",f); if (index(f,a) || index(f,b)) print "    "$0}' \
    | head -6
done
if [ "${MISSING_CLONE}" = "1" ]; then
  echo "  [i] 写 ⑤ 前先跑（单独一条 Bash，timeout 设 300000）："
  echo "      python3 ${DIR}/fetch_ref_impl.py --op ${OP}"
  echo "      走镜像链（jsDelivr→ghproxy→raw）取上游 kernel 源缓存到 /tmp/ref_impl/ 供 Read。"
  echo "      禁止直接 WebFetch/curl raw.githubusercontent.com（企业网被墙）；取不到时对比表"
  echo "      该源如实记 UNREACHABLE，禁止凭记忆补「算法要点」。"
fi
echo "==> 上述命中 + 仓内相似算子（decision2 候选段、SKILL.md「实现」节参考表）= 对比表三类取材来源；"
echo "    动笔 ⑤ 前必须呈现「参考实现对比表」（来源｜算法要点｜边界情况处置｜采纳/不采纳+理由）。"

cd "${ROOT}" || exit 1
# 容错常见仓库布局：传入的是上一层（集成仓库的 submodule 顶层）时自动下钻一级
if [ ! -f schema/ops.fbs ] && [ -f mindspore-lite/schema/ops.fbs ]; then
  cd mindspore-lite || exit 1
  echo "[i] ${ROOT} 下未见 schema/ops.fbs，已自动进入 $(pwd)"
fi
if [ ! -f schema/ops.fbs ]; then
  echo "[!] ${ROOT} 不是 mindspore-lite 代码根目录（缺 schema/ops.fbs，其下也无 mindspore-lite/schema/ops.fbs）——传入正确根目录重跑" >&2
  exit 1
fi

# s <标签> <grep 命令...>：执行扫描，0 命中显式输出「缺失」
s() {
  local label="$1"; shift
  echo "--- ${label} ---"
  "$@" || echo "(0 命中 → 缺失)"
}

echo
echo "############ decision2 复用候选排查: ${OP}（确切名 0 命中 ≠ 新建 PrimitiveType 的定论） ############"
# 候选发现共四层，前三层机械、第四层是已确认等价关系的缓存——没有一层是全集，
# 合并后仍须 SKILL.md decision2 的人工语义检索兜底；等价性一律按 decision2 四条以仓内 infer/kernel 裁决。
# 候选来源①：去版本后缀的基名（XxxV2 → Xxx）——源框架的 vN 变体常映射到已有 PrimType
BASE="$(printf '%s' "${OP}" | sed -E 's/V[0-9]+$//')"
CANDS="${BASE}"
# 候选来源②：schema union 成员的大小写不敏感**双向**子串匹配
#   正向：成员名含算子基名（Tile → TileFusion）；反向：算子基名含成员名（Concatenation ⊃ Concat），
#   反向要求成员名 ≥4 字符防短名噪声。
UNION="$(sed -n '/union PrimitiveType {/,/^}/p' schema/ops.fbs | grep -oE '[A-Za-z0-9_]+' | grep -v '^union$\|^PrimitiveType$')"
BASE_LC="$(printf '%s' "${BASE}" | tr '[:upper:]' '[:lower:]' | tr -d '_')"
for m in ${UNION}; do
  M_LC="$(printf '%s' "$m" | tr '[:upper:]' '[:lower:]')"
  case "${M_LC}" in *"${BASE_LC}"*) CANDS="${CANDS} $m"; continue ;; esac
  if [ "${#M_LC}" -ge 4 ]; then
    case "${BASE_LC}" in *"${M_LC}"*) CANDS="${CANDS} $m" ;; esac
  fi
done
# 候选来源③：跨框架映射字典（tf2onnx @tf_op 注册表）——对**任意**算子通用的异名同义引擎：
#   TF/TFLite 名 ↔ ONNX 名的权威映射；ONNX 名通常直接对得上 schema union / 已有 parser。
echo "--- 候选来源③：跨框架映射字典（取不到时跨名候选改靠人工语义检索，不可省） ---"
XREF="$(python3 "${DIR}/fetch_op_spec.py" --op "${OP}" --cross-ref 2>/dev/null)"
if [ -n "${XREF}" ]; then
  printf '%s\n' "${XREF}"
  CANDS="${CANDS} $(printf '%s\n' "${XREF}" | sed -n 's/^CROSS_REF_CANDIDATES: //p')"
else
  echo "(字典探测失败)"
fi
# 候选来源④：同义词簇缓存——历次 decision2 裁决确认过的等价族沉淀于此（格式：ERE正则;候选列表，
#   对算子小写去下划线全名锚定匹配）。这是缓存不是全集：decision2 人工检索发现表外新等价族时，
#   **把它追加成一行**（skill 的自维护机制，替代跨会话 memory）。
OP_KEY="$(printf '%s' "${OP}" | tr '[:upper:]' '[:lower:]' | tr -d '_')"
while IFS=';' read -r pat cands; do
  case "${pat}" in ''|'#'*) continue ;; esac
  if printf '%s' "${OP_KEY}" | grep -qE "^(${pat})$"; then CANDS="${CANDS} ${cands}"; fi
done <<'CLUSTERS'
select|selectv[0-9]*|where|nonzero;Select Where
mean|sum|reduce[a-z]*;ReduceFusion
pack;Stack
unpack;Unstack
expanddims|unsqueeze;ExpandDims Unsqueeze
fullyconnected|gemm|matmul|batchmatmul[a-z0-9]*;FullConnection MatMulFusion
transposeconv|convtranspose|deconv[a-z0-9]*;Conv2dTransposeFusion
conv|conv[0-9]*d|depthwiseconv[0-9a-z]*;Conv2DFusion
[a-z]*pool[0-9a-z]*;AvgPoolFusion MaxPoolFusion
resize[a-z]*|upsample;Resize
mirrorpad|pad|padv[0-9]*;PadFusion
pow[a-z]*|power;PowFusion
div|realdiv;DivFusion
mul|multiply;MulFusion
sub|subtract;SubFusion
add|addn;AddFusion
logistic|sigmoid|hardsigmoid|relu[0-9a-z]*|tanh|hardswish|elu|gelu|silu|swish|mish|softplus|leakyrelu|prelu;Activation LeakyRelu PReLUFusion
embeddinglookup;Gather
quantize|dequantize;QuantDTypeCast
slice|stridedslice;SliceFusion StridedSlice
topk[v0-9]*;TopKFusion
batchnorm[a-z]*|fusedbatchnorm[a-z]*;BatchNorm FusedBatchNorm
l2normalization;L2NormalizeFusion
CLUSTERS
FOUND=0
for c in $(printf '%s\n' ${CANDS} | sort -u); do
  [ "$c" = "${OP}" ] && continue
  grep -qE "^[[:space:]]+${c},?[[:space:]]*$" schema/ops.fbs || continue
  FOUND=1
  echo "--- 候选 PrimitiveType_${c}（已有链路概览，细节用 scan_op.sh ${c} 重跑） ---"
  grep -rln "${c}" tools/converter/parser/onnx/ tools/converter/parser/tflite/ --include="*.cc" 2>/dev/null | head -4 | sed 's/^/  parser:   /'
  grep -rln "REG_POPULATE.*${c}," src/common/ops/populate/ --include="*.cc" 2>/dev/null | sed 's/^/  populate: /'
  grep -rln "REG_INFER(${c}," src/litert/kernel/cpu/nnacl_c/infer/ --include="*.c" 2>/dev/null | sed 's/^/  infer:    /'
  grep -rln "REG_KERNEL_CREATOR(PrimType_${c},\|REG_KERNEL(kCPU.*PrimitiveType_${c}," src/litert/kernel/cpu/ --include="*.c" --include="*.cc" 2>/dev/null | sed 's/^/  kernel:   /'
  grep -rln "REG_OPERATOR_CODER.*PrimitiveType_${c}," tools/converter/micro/coder/opcoders/ --include="*.cc" 2>/dev/null | sed 's/^/  opcoder:  /'
  # 语义证据：候选 PrimType 的语义真值在仓内 infer/kernel，不在任何框架同名算子的摘要里
  INFER_F=$(grep -rln "REG_INFER(${c}," src/litert/kernel/cpu/nnacl_c/infer/ --include="*.c" 2>/dev/null | head -1)
  KERNEL_F=$(grep -rln "REG_KERNEL_CREATOR(PrimType_${c},\|REG_KERNEL(kCPU.*PrimitiveType_${c}," src/litert/kernel/cpu/ --include="*.c" --include="*.cc" 2>/dev/null | head -1)
  for sf in ${INFER_F} ${KERNEL_F}; do
    echo "  语义证据 ${sf}（输入个数分支/广播痕迹——裁决前必须 Read 通读此文件，下列行只是索引）:"
    HITS=$(grep -n "inputs_size\|in_size\|roadcast\|Single\|Triple" "${sf}" 2>/dev/null | head -8)
    if [ -n "${HITS}" ]; then printf '%s\n' "${HITS}" | sed 's/^/    /'; else echo "    (无模式命中——语义形态非典型，更必须通读该文件)"; fi
  done
done
[ "${FOUND}" = "1" ] || echo "(本脚本未发现机械候选——仍须按下行人工再查一轮)"
echo "==> 候选只是线索：再用 decision1 语义摘要的核心语义（条件选择/广播/索引…）检索 ops.fbs 与 parser 目录；源框架文档常注明等价算子。"
echo "==> 同名异义警告：候选语义只能从上列仓内 infer/kernel（Read 通读）与已映射框架的规格读出；禁止拿与候选同名的"
echo "    其它框架算子摘要当其语义（实证：同名算子在 ONNX 是三输入广播选择、在 TFLite 是返回坐标的单输入算子）。"
echo "    多模态 kernel 按输入个数分支承载多形态——逐分支裁决，目标算子与某分支逐项等价即复用该分支。"
echo "==> 候选语义等价（decision2 四条全符）→ 走复用分支只补缺失环节；走新建分支必须在 decision4 呈现「已排查候选 + 不等价理由」，每条理由附 文件:行/规格证据。"

echo
echo "############ decision4 链路扫描: ${OP} @ $(pwd) ############"
s "① Schema (schema/ops.fbs + ops_def.cc)" \
  grep -n "${OP}" schema/ops.fbs src/common/ops/ops_def.cc
s "①′ ops::${OP} 原型类 (子模块自动生成 或 本地 primitive/，没有则需手写)" \
  grep -rln "class OPS_API ${OP} " ../mindspore/mindspore/ops/ src/common/ops/primitive/
s "①‴ ANF→schema 导出注册 (ops_utils.cc，最易漏)" \
  grep -n "REG_MINDSPORE_OPERATOR(${OP})" src/common/ops/ops_utils.cc
s "② Parser (onnx + tflite)" \
  grep -rln "${OP}" tools/converter/parser/onnx/ tools/converter/parser/tflite/ --include="*.cc"
s "③ Populate (命中 custom_populate.cc = Custom 捷径，红线 1)" \
  grep -rn "REG_POPULATE.*${OP}" src/common/ops/populate/ --include="*.cc"
s "④ Infer" \
  grep -rn "REG_INFER.*${OP}" src/litert/kernel/cpu/nnacl_c/infer/ --include="*.c"
s "⑤ Kernel 注册 (KernelBase / LiteKernel)" \
  grep -rn "REG_KERNEL_CREATOR.*${OP}\|REG_KERNEL(kCPU.*${OP}" src/litert/kernel/cpu/ --include="*.c" --include="*.cc"
# ⑤′ 运行时 kernel 的 int8 数据通路——不只查注册存在性。FULL_QUANT 的 bias_correction 在
# 宿主运行时执行 int8 模型：kernel 文件「已有」但无 int8 处理时，int8 转换阶段才以堆越界/
# 卡死暴露（排查代价最高的漏检）。复用分支最常见的隐性缺口正是「⑤ 标已有，实际仅 fp32」。
echo "--- ⑤′ 运行时 kernel int8 数据通路（grep 启发式；有痕迹也仍须人工核对重量化与快路） ---"
KFILES=$(grep -rl "REG_KERNEL_CREATOR.*${OP}\|REG_KERNEL(kCPU.*${OP}" src/litert/kernel/cpu/ --include="*.c" --include="*.cc" 2>/dev/null)
if [ -z "${KFILES}" ]; then
  echo "(无 ⑤ kernel 注册 → 本项随 ⑤ 一并新建)"
else
  for f in ${KFILES}; do
    if grep -q "kNumberTypeInt8\|int8_t" "${f}"; then
      echo "  ${f}: 有 int8 痕迹——仍须核对：int8 数据经逐输入重量化？快路(memcpy/MoveData/单元素)对 int8 安全？（实现指南 ⑤″ 第 6 条全执行路径审计）"
    else
      echo "  ${f}: 未见 int8 处理 → 链路表 ⑤ 只能标「已有(仅fp32)」，int8 分支列入缺失（按实现指南 ⑤‴ 模板补）"
    fi
  done
fi
s "⑥ OpCoder (命中 REG_BUILIN_CUSTOM_CODER = Custom 捷径，红线 1)" \
  grep -rn "REG_OPERATOR_CODER.*${OP}\|REG_BUILIN_CUSTOM_CODER.*${OP}" tools/converter/micro/coder/opcoders/ --include="*.cc"
s "⑦ 量化器支持列表" \
  grep -n "kPrim${OP}\|${OP}" tools/converter/quantizer/full_quant_quantizer.cc

echo
echo "############ ⑧ 融合/图改写审计: ${OP}（decision3 开关3 + 开关3′ 与 step4 融合审计的机械证据，勿凭记忆断言） ############"
# decision3 开关3「组合算子需融合 pass?」+ 开关3′「本算子被既有图 pass 消除/重写?」一律据此段裁决，不得凭记忆写"框架不拆此算子/不删此算子"。
#   命中 = 有 pass 产出/消费本算子的子图——裁决前必须读懂其 DefinePattern/Process；
#   0 命中 = 无既有融合涉及本算子（绝大多数独立算子如此，开关3 填「否」的证据）。
echo "--- tools/optimizer/fusion/ 命中（按算子名 + 去版本基名，大小写不敏感） ---"
FUS=$(grep -rilnE "${OP}|${BASE}" tools/optimizer/fusion/ --include="*.cc" --include="*.h" 2>/dev/null | sort -u)
if [ -n "${FUS}" ]; then printf '%s\n' "${FUS}" | sed 's/^/  /'; else echo "  (0 命中 —— 无既有 fusion pass 涉及本算子)"; fi
echo "--- tools/optimizer/graph/ 命中 ---"
GRA=$(grep -rilnE "${OP}|${BASE}" tools/optimizer/graph/ --include="*.cc" --include="*.h" 2>/dev/null | sort -u)
if [ -n "${GRA}" ]; then printf '%s\n' "${GRA}" | sed 's/^/  /'; else echo "  (0 命中)"; fi
echo "==> 命中文件须在 decision3 开关3 裁决前读懂：fusion 产出本算子=另一前端路径（仍需全 ②–⑦ 通路），"
echo "    消费本算子=某些图会被吸收（独立通路仍必需）；二者都不替代 ②–⑦。0 命中=开关3 填「否」。"
echo "==> 反向陷阱：若源框架把本算子表达为子图（HardSwish/GeLU/Swish 等），0 命中意味着\"缺融合 pass\"→须新建（开关3 填「是」）；"
echo "    判别看 decision1 语义摘要——本算子在源框架是单算子还是被拆成 Mul/Add/Relu6 等子图。"
echo
echo "--- graph/ 中「消除/重写型」命中（含 Remove/redundant/Eliminat 等擦除模式，decision3 开关3′ 的机械证据）---"
DESTROY=""
if [ -n "${GRA}" ]; then
  DESTROY=$(printf '%s\n' "${GRA}" | xargs grep -ilE "[Rr]emove|[Rr]edundant|[Ee]liminat|DropoutRemove|isa<" 2>/dev/null | sort -u)
fi
if [ -n "${DESTROY}" ]; then printf '%s\n' "${DESTROY}" | sed 's/^/  /'; else echo "  (0 命中 —— 无既有「消除/重写型」pass 涉及本算子)"; fi
echo "==> 开关3′「本算子被既有图 pass 消除/重写?」：上面「消除/重写型」段非空 = 本算子可能在转换期被既有 pass 整体删除或替换"
echo "    （passthrough/no-op 类常见：Identity、推理期 Dropout、同 dtype Cast、空 Reshape）。这是合法优化——不禁用、不据此跳过 ①–⑦"
echo "    （算子在该 pass 未触发的图里仍可达，仍须全做）；但忽略它 = ①–⑦ 可能是不可达死代码、step7 在被改写的空图上假绿。命中则必须："
echo "    (a) 读懂命中 pass 的 DefinePattern/Process，写出本算子「何时被删 / 何时存活」（单消费者? 非图输出? 前后 dtype/shape 一致?）→ 落 docs/decision.md；"
echo "    (b) step7 能力清单含一条「该 pass 不触发、算子真正到达 kernel」用例（⑤/⑥/⑦ 与 INT8 genuine 的唯一落点），并对「该 pass 触发、算子被合法删除」情形给出用例与结果说明（输出仍正确，但不得据此声称 kernel 覆盖）。"
echo "    0 命中=开关3′ 填「否」。"

echo
echo "==> 完整输出已存 ${LOG} —— 若上方有内容因管道截断丢失（如 decision1 语义摘要段），从该文件读全文。"
echo "==> opset/属性需要补查时: python3 ${DIR}/fetch_op_spec.py --op ${OP}（或照抄 references/spec-sources.md 的单行命令）。禁止现场手写 onnx.defs 内省脚本——OpSchema 字段名靠猜，实证连错 4 次纯属浪费。"
echo "==> 下一步(step2): 读 references/worked-example.md，做 decision2 复用/新建裁决（候选见上方 decision2 段；详细流程 references/decision2-reuse-decision.md）。"
echo "==> 再下一步(step3): 据本输出填 decision4 三件产物（框架对应表+链路表+能力清单）呈现给用户后，才进实现。"
echo "==> 注意: build/ 是生成产物不要当源头查；schema 真值在 schema/ops.fbs。"
