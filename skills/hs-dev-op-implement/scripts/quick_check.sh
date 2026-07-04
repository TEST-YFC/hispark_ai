#!/bin/bash
# Copyright 2026 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# quick_check.sh <mindspore-lite 代码根目录> [file.c|file.cc ...]
#
# 构建前预检（秒级）：对本次新建/修改的 .c/.cc 跑编译器 -fsyntax-only。
# narrowing、未声明变量、非法 cast 这类错误在这里几秒暴露——漏进真实构建一轮要 10–30 分钟。
# 不带 file 参数时自动从 git status 取未提交的 .c/.cc（含未跟踪新文件）。
#
# 编译参数来源（决定预检可信度）：
#   首选 上一轮构建的 compile_commands.json——按「同文件」或「同目录同后缀兄弟文件」取真实
#   参数（新算子文件几乎总是落在已有目录，兄弟参数即其真实参数），verdict 可信；
#   无 compile_commands 时降级为手拼 include 集——纯 C（nnacl_c）仍可定案，
#   C++ 文件头依赖深、手拼不可靠，只报 UNVERIFIED 不误伤。
#
# 逐文件四态：
#   PASS           预检通过
#   FAIL           真实代码错误——必须修复并重跑预检；存在 FAIL 时禁止启动 build_mslite.sh
#   SCHEMA_PENDING 仅缺 schema 生成类型（XxxT/PrimitiveType_Xxx/value_as_Xxx，且 Xxx 是本次
#                  ops_def.cc 新增的 OP_TYPE）——这些类型要到构建期才由 schema_gen+flatc 产出，
#                  预检阶段必然报错，不阻塞构建；除此之外有任何独立错误仍判 FAIL
#   UNVERIFIED     预检层无法定案（缺头/无编译参数）——不阻塞构建，构建失败时优先怀疑这些文件
# 退出码：存在 FAIL 时为 1，否则 0。
set -u

ROOT="${1:?用法: quick_check.sh <mindspore-lite 代码根目录> [file ...]}"
shift || true
cd "${ROOT}" || exit 2
# 容错常见仓库布局：传入的是上一层（集成仓库的 submodule 顶层）时自动下钻一级
if [ ! -f schema/ops.fbs ] && [ -f mindspore-lite/schema/ops.fbs ]; then
  cd mindspore-lite || exit 2
fi
if [ ! -f schema/ops.fbs ]; then
  echo "[!] ${ROOT} 不是 mindspore-lite 代码根目录（缺 schema/ops.fbs）" >&2
  exit 2
fi

# ---- 待检文件：显式传入，或自动取 git 未提交的 .c/.cc ----
FILES=("$@")
if [ ${#FILES[@]} -eq 0 ]; then
  # git --porcelain 输出的路径相对仓库顶层（与 cwd 无关），统一拼成绝对路径
  TOP="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  while IFS= read -r f; do FILES+=("${TOP:+${TOP}/}${f}"); done < <(
    git status --porcelain 2>/dev/null | awk '{print $NF}' | grep -E '\.(c|cc)$' || true)
fi
# ---- 链接性 lint：nnacl_c 函数声明头必须带 extern "C" 守卫 ----
# -fsyntax-only 抓不到链接性错误：nnacl_c 的 .c 按 C 编译，C++ 侧（LiteKernel/coder/serializer）
# include 其 .h 时若无 extern "C"，符号按 C++ mangle 解析 → 链接期 undefined reference，
# 烧一轮 10–30 分钟构建才暴露（实证事故：新建 int8 头漏守卫）。此处秒级拦截。
# 适用域 = 仓内既有文件 100% 带守卫的函数声明目录（fp32/int8/fp16/infer/base）；
# kernel/ 走 KernelBase 体系、*_parameter.h 仅含结构体，均不在此列。
LINT_FAIL=0
HDRS=()
for a in "$@"; do case "$a" in *.h) HDRS+=("$a");; esac; done
if [ ${#HDRS[@]} -eq 0 ]; then
  TOP2="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  while IFS= read -r f; do HDRS+=("${TOP2:+${TOP2}/}${f}"); done < <(
    git status --porcelain 2>/dev/null | awk '{print $NF}' | grep -E '\.h$' || true)
fi
for h in "${HDRS[@]}"; do
  [ -f "${h}" ] || continue
  case "${h}" in
    *nnacl_c/fp32/*|*nnacl_c/int8/*|*nnacl_c/fp16/*|*nnacl_c/infer/*|*nnacl_c/base/*)
      if ! grep -q 'extern "C"' "${h}"; then
        echo "[FAIL] ${h}："
        echo "    缺 extern \"C\" 守卫——C++ 调用方链接期将报 undefined reference（编译期不报）。"
        echo "    修法（与同目录所有既有头一致）：声明区包入"
        echo "      #ifdef __cplusplus"
        echo "      extern \"C\" {"
        echo "      #endif"
        echo "      ... 函数声明 ..."
        echo "      #ifdef __cplusplus"
        echo "      }"
        echo "      #endif"
        LINT_FAIL=$((LINT_FAIL+1))
      fi ;;
  esac
done

# ---- rank 上界一致性 advisory（非阻塞，不计入退出码） ----
# 固定长 shape 数组（[DIMENSION_xD]）的越界是本 skill 反复踩的坑，-fsyntax-only 全抓不到，分三类：
#  (1) 多常量不一致：infer/kernel/coder 取了不同 DIMENSION_xD（实证 Hardmax：infer 8D / int8 数组 5D，
#      4D 过、6D 静默算错）。
#  (2) 数组在、守卫缺：某 .h 开了 [DIMENSION_xD] 数组，但它与同 stem 的 .c/.cc 内均无 > DIMENSION_xD 守卫；
#      填充循环（for i<n_dim 直写 input_shape_[i]）在 rank 超界时越界（实证 Hardmax：kernel/hardmax.{h,c}
#      数组开 4D、InitHardmaxParam 无守卫，5D 模型 fp32 校准期越界——各层常量都是 4D，(1) 查不出，仍越界）。
#  (3) infer 不设闸：改动集里有定长数组层、且某数组层已被 (2) 判为无守卫，而 *_infer.c 内也无任何
#      DIMENSION_* 守卫——传播边界没拒绝超界 rank，5D 模型 infer 放行、到 kernel 才越界。
# 不变量（两条都要）：① 各层数组/守卫取同一 DIMENSION_* 常量；② infer 是权威上界闸门——在任何定长数组层
# 被触达前显式拒绝 rank>上限，且每个 [DIMENSION_xD] 数组的填充循环前都有 > DIMENSION_xD 守卫。
RANK_LINES=""
ARR_FILES=()      # 声明了 [DIMENSION_xD] 定长数组的文件
GUARD_STEMS=()    # 带 > / >= / < / <= DIMENSION_xD 守卫的文件 stem（去后缀文件名）
INFER_FILES=()    # 改动集中的 *_infer.c|cc
# 显式传参时 .h 同时落在 FILES 与 HDRS，去重避免重复打印
while IFS= read -r f; do
  [ -n "${f}" ] && [ -f "${f}" ] || continue
  arr="$(grep -nE '\[[[:space:]]*DIMENSION_[0-9]+D' "${f}" 2>/dev/null)"
  grd="$(grep -nE '[<>]=?[[:space:]]*DIMENSION_[0-9]+D' "${f}" 2>/dev/null)"
  # 数组维度 + 上界守卫两类上下文一并收进显示缓冲（降噪）
  both="$(printf '%s\n%s' "${arr}" "${grd}" | grep -nE 'DIMENSION_[0-9]+D' 2>/dev/null)"
  [ -n "${arr}${grd}" ] && RANK_LINES="${RANK_LINES}$(grep -nE '(\[[[:space:]]*DIMENSION_[0-9]+D)|([<>]=?[[:space:]]*DIMENSION_[0-9]+D)' "${f}" | sed "s#^#    ${f##*/}:#")"$'\n'
  stem="${f##*/}"; stem="${stem%.*}"
  [ -n "${arr}" ] && ARR_FILES+=("${f}")
  [ -n "${grd}" ] && GUARD_STEMS+=("${stem}")
  case "${f}" in *_infer.c|*_infer.cc) INFER_FILES+=("${f}") ;; esac
done < <(printf '%s\n' "${FILES[@]}" "${HDRS[@]}" | awk 'NF && !seen[$0]++')
RANK_DISTINCT="$(printf '%s' "${RANK_LINES}" | grep -oE 'DIMENSION_[0-9]+D' | sort -u)"
RANK_N="$(printf '%s\n' "${RANK_DISTINCT}" | grep -c .)"

# (1) 多个不同上界并存
if [ "${RANK_N}" -gt 1 ]; then
  echo "[i] rank advisory (1)：shape 数组/守卫出现多个不同上界 —— $(printf '%s' "${RANK_DISTINCT}" | tr '\n' ' ')"
  echo "    核对 infer / runtime kernel / nnacl kernel / OpCoder 是否应取同一 DIMENSION_xD（实证 Hardmax：infer 8D / int8 数组 5D，6D 静默算错）："
  printf '%s' "${RANK_LINES}"
fi

# (2) 定长数组所在 stem 单元内无任何 > DIMENSION_xD 守卫
FLAG2=0
if [ "${#ARR_FILES[@]}" -gt 0 ]; then
  for af in "${ARR_FILES[@]}"; do
    astem="${af##*/}"; astem="${astem%.*}"
    hit=0
    if [ "${#GUARD_STEMS[@]}" -gt 0 ]; then
      for gs in "${GUARD_STEMS[@]}"; do [ "${gs}" = "${astem}" ] && { hit=1; break; }; done
    fi
    if [ "${hit}" -eq 0 ]; then
      FLAG2=1
      echo "[i] rank advisory (2)：${af##*/} 声明了 [DIMENSION_xD] 定长数组，但它与同名 .c/.cc 内均无 > DIMENSION_xD 守卫。"
      grep -nE '\[[[:space:]]*DIMENSION_[0-9]+D' "${af}" | sed "s#^#        ${af##*/}:#"
      echo "        填充循环按 n_dim 直写数组将在 rank 超界时越界——在写入前加显式守卫（实证 Hardmax：kernel/hardmax.c InitHardmaxParam）。"
    fi
  done
fi

# (3) 存在无守卫数组层时，再查 infer 是否也漏设闸门（infer 应是权威上界闸门）
if [ "${FLAG2}" -eq 1 ] && [ "${#INFER_FILES[@]}" -gt 0 ]; then
  for inf in "${INFER_FILES[@]}"; do
    if ! grep -qE '[<>]=?[[:space:]]*DIMENSION_[0-9]+D' "${inf}" 2>/dev/null; then
      echo "[i] rank advisory (3)：${inf##*/} 无任何 DIMENSION_* 守卫，传播边界未拒绝超界 rank。"
      echo "        infer 是 rank 权威闸门，应在此显式 return 报错（5D 模型若在 infer 放行，则到 kernel 才越界）。"
    fi
  done
fi

# ---- ⑥ opcoder 内联计算循环 advisory（非阻塞） ----
# ⑥ 红线：DoCode 只发"数据 + 调用"，计算/广播逻辑应落在 nnacl_c 函数里，runtime 与 codegen 调同一个。
# 把整段 select/requant/广播 stride 循环内联进 coder（code << "for (...)"）有三宗罪：与 runtime 发散、
# 改编译错时易被整段删、stride 数学在 10 分钟构建环里反复试错（实证：广播 Where coder 内联 stride 连错 3 轮）。
# 既有 matmul/gather 等有合法脚手架循环，无法一刀切判 FAIL，故仅对本次改动的 opcoder 文件给 advisory。
for f in "${FILES[@]}"; do
  case "${f}" in
    */opcoders/*.cc)
      ih="$(grep -nE '<<[^;]*"[^"]*(for|while)[[:space:]]*\(' "${f}" 2>/dev/null)"
      if [ -n "${ih}" ]; then
        echo "[i] opcoder advisory：${f##*/} 内联发射了 for/while 循环——确认是脚手架（索引/打包/地址计算），"
        echo "    而非把计算/广播逻辑内联（计算须在 nnacl_c 函数里、runtime 与 coder 调同一个；见实现指南 ⑥ / ⑤⁗）："
        printf '%s\n' "${ih}" | sed "s#^#        ${f##*/}:#"
      fi ;;
  esac
done

# ---- ⑤″ condition/index 首输入算子 dtype 派发 advisory（非阻塞） ----
# 这类算子在 bool/int 键注册（派发键 = 首输入 dtype），运行时 kernel 的 data_type_ 字段装的就是该派发键，
# 不是数据张量 dtype。按 data_type_ == kNumberTypeInt8 分 int8 分支会恒假（死分支），int8 数据被按 fp32
# 重解释 → 转换期野指针（实证：广播 Where int8 崩溃）。应改读 in_[<数据输入下标>]->data_type_。
for f in "${FILES[@]}"; do
  case "${f}" in
    *nnacl_c/kernel/*.c|*nnacl_c/base/*.c|*/cpu/base/*.cc)
      if grep -qE 'kNumberTypeBool' "${f}" 2>/dev/null \
         && grep -qE 'data_type_[[:space:]]*==[[:space:]]*kNumberTypeInt8' "${f}" 2>/dev/null; then
        echo "[i] dtype-dispatch advisory：${f##*/} 在含 bool 注册键的算子里按 data_type_ == kNumberTypeInt8 分支——"
        echo "    确认 data_type_ 是数据张量 dtype 而非派发键（condition/index 首输入算子此字段 = 首输入 dtype，"
        echo "    误用会让 int8 分支恒假 → 数据按 fp32 重解释 → 野指针）。正解：读 in_[<数据输入下标>]->data_type_。"
        grep -nE 'data_type_[[:space:]]*==[[:space:]]*kNumberTypeInt8' "${f}" | sed "s#^#        ${f##*/}:#"
      fi ;;
  esac
done

if [ ${#FILES[@]} -eq 0 ]; then
  if [ ${LINT_FAIL} -gt 0 ]; then
    echo "[!] 头文件 lint 存在 FAIL=${LINT_FAIL}——修复后重跑本脚本，再启动 build_mslite.sh"
    exit 1
  fi
  echo "无待检 .c/.cc（git 下无未提交改动且未显式传文件）"
  exit 0
fi

# ---- SCHEMA_PENDING 白名单：本次 git 未提交的 ops_def.cc 新增 OP_TYPE/OP_SCHEMA_DEF 算子名 ----
# 名字必须命中此名单才豁免——拼写错误的 schema 成员引用（HardmxT 之类）不在名单内，照常 FAIL
PENDING_OPS="$(git diff HEAD 2>/dev/null -- '*ops_def.cc' \
  | grep -oP '^\+\s*OP_(TYPE|SCHEMA_DEF)\(\K\w+' | sort -u | tr '\n' ' ')"

# ---- 原生整型 dtype 覆盖 advisory（非阻塞） ----
# 量化 INT8 豁免 != 跳过规格里的 int8/uint8 派发键。ConvInteger/Quantize/Cast 等原生整型
# 算子常见输入 dtype 是 int8 与 uint8；弱模型容易只注册 kNumberTypeInt8，直到 hs-verify-op 的
# uint8 用例才暴露。这里按本次新增 OP_TYPE 与 mslite-op-output/<op>/scripts 下的 spec/checklist
# 做保守提示，不作为 FAIL：有些算子确实只支持 int8 或只支持 uint8，最终以规格与能力清单为准。
for op in ${PENDING_OPS:-}; do
  OPDIRS=()
  for base in ../../mslite-op-output ../mslite-op-output ../../../mslite-op-output; do
    [ -d "${base}/${op}/scripts" ] && OPDIRS+=("${base}/${op}/scripts")
  done
  [ ${#OPDIRS[@]} -gt 0 ] || continue
  WANT_UINT8=0
  WANT_NATIVE_HINT=0
  for d in "${OPDIRS[@]}"; do
    grep -Rqi 'uint8' "${d}/op_spec.py" "${d}/capability_checklist.json" 2>/dev/null && WANT_UINT8=1
    grep -RqiE 'uint8|原生|native|quantization[-_ ]*exempt|int8[-_ ]*exempt|量化.*豁免' \
      "${d}/op_spec.py" "${d}/capability_checklist.json" 2>/dev/null && WANT_NATIVE_HINT=1
  done

  # 原生 dtype-only 算子不应把实现伪装成 fp32 路径。这里按 opdir 的用例/清单给
  # 非阻塞提示：确有 float 路径的算子可以忽略；若只是 int8/uint8/int32/bool 规格，
  # 应改放 nnacl_c/int8、nnacl_c/base 或 opcoders/base/nnacl/int8。
  if [ "${WANT_NATIVE_HINT}" -eq 1 ]; then
    op_snake="$(printf '%s' "${op}" | sed -E 's/([A-Z]+)([A-Z][a-z])/\1_\2/g; s/([a-z0-9])([A-Z])/\1_\2/g' | tr '[:upper:]' '[:lower:]')"
    HAS_NATIVE_IN_FP32=0
    for f in "${FILES[@]}"; do
      case "${f}" in
        */nnacl_c/fp32/*"${op_snake}"*|*/opcoders/nnacl/fp32/*"${op_snake}"*)
          HAS_NATIVE_IN_FP32=1 ;;
      esac
    done
    if [ "${HAS_NATIVE_IN_FP32}" -eq 1 ]; then
      echo "[i] native-dtype placement advisory：${op} 的 op_spec/capability_checklist 显示原生整型/离散 dtype 线索，但本次改动有同名文件落在 fp32 目录。"
      echo "    fp32/ 只放真实 float 计算路径；原生 int8/uint8/int32/bool 算子应按语义放 nnacl_c/int8、nnacl_c/base、opcoders/nnacl/int8 或 opcoders/base。"
      echo "    若该算子确实同时支持 float 输入，请确认 fp32 文件只承载 float 路径，原生 dtype 另有独立注册和计算入口。"
    fi
  fi

  [ "${WANT_UINT8}" -eq 1 ] || continue
  HAS_KERNEL_UINT8=0
  HAS_CODER_UINT8=0
  for f in "${FILES[@]}"; do
    [ -f "${f}" ] || continue
    grep -q "REG_KERNEL_CREATOR(PrimType_${op},[[:space:]]*kNumberTypeUInt8" "${f}" 2>/dev/null && HAS_KERNEL_UINT8=1
    grep -q "REG_OPERATOR_CODER(.*kNumberTypeUInt8,.*PrimitiveType_${op}" "${f}" 2>/dev/null && HAS_CODER_UINT8=1
  done
  if [ "${HAS_KERNEL_UINT8}${HAS_CODER_UINT8}" != "11" ]; then
    echo "[i] native-dtype advisory：${op} 的 op_spec/capability_checklist 提到 uint8，但本次改动未同时看到 uint8 kernel/coder 注册。"
    echo "    量化 INT8 豁免只跳过量化器/genuine 符号检查；规格原生 dtype（int8/uint8/int32/bool...）仍须逐 dtype 注册。"
    echo "    若规格确不支持 uint8，请修正能力清单；若支持，请补 REG_KERNEL_CREATOR/REG_OPERATOR_CODER 的 kNumberTypeUInt8。"
  fi
done


# ---- 首选：compile_commands.json（上一轮构建产物，参数即真实参数） ----
DBS="$(find ../build build .. . -maxdepth 3 -name compile_commands.json 2>/dev/null | sort -u | tr '\n' ':' )"
if [ -n "${DBS}" ] && command -v python3 >/dev/null 2>&1; then
  python3 - "${DBS}" "${PENDING_OPS}" "${FILES[@]}" <<'PYEOF'
import json, os, re, shlex, subprocess, sys

db_paths = [p for p in sys.argv[1].split(":") if p]
pending_ops = set(sys.argv[2].split())
files = sys.argv[3:]
by_file, by_dir = {}, {}
for p in db_paths:
    try:
        entries = json.load(open(p))
    except Exception:
        continue
    for e in entries:
        f = e.get("file", "")
        if not os.path.isabs(f):
            f = os.path.join(e.get("directory", "."), f)
        f = os.path.normpath(f)
        by_file.setdefault(f, e)
        by_dir.setdefault((os.path.dirname(f), os.path.splitext(f)[1]), e)

def schema_pending(err_lines):
    """新建 PrimitiveType 时，schema 生成类型（XxxT / PrimitiveType_Xxx / value_as_Xxx）要到
    构建期才由 schema_gen+flatc 产出，预检阶段必然报错。仅当：
      ① 至少一条错误指向 pending 名单内算子的 schema 成员，且
      ② 其余全部 error 行都是它的已知级联（template argument / make_unique / <expression error> / did you mean）
    才判 SCHEMA_PENDING（不阻塞构建）。任何独立错误、或名单外名字（疑似拼写错误）→ 照常 FAIL。"""
    if not pending_ops:
        return False
    q = "['‘’]"  # GCC 在 UTF-8 locale 下用弯引号 ‘ ’，C locale 用 ASCII '
    member = re.compile(
        # XxxT / PrimitiveType_Xxx 同一缺失，GCC 随上下文在两种措辞间切换：
        # 值表达式处报 "is not a member of 'schema'"，case 标签/限定作用域处报
        # "has not been declared in 'schema'"（实证 Hardmax 的 populate/coder 命中后者，
        # 旧正则只收前者 → 误判 FAIL）。两种都收。
        q + r"(?:(\w+?)T|PrimitiveType_(\w+))" + q
        + r" (?:is not a member of|has not been declared in) "
        + q + r"(?:mindspore::)?schema" + q
        + "|has no member named " + q + r"value_as_(\w+)" + q
        # 裸作用域形式：'PrimitiveType_Xxx' was not declared in this scope（无 schema 限定，
        # 靠下方 pending 名单兜底——名单外名字即疑似拼写错误，仍 FAIL）
        + "|" + q + r"PrimitiveType_(\w+)" + q + r" was not declared in this scope")
    cascade = re.compile(
        r"template argument \d+ is invalid|no matching function for call to .{0,3}make_unique"
        r"|<expression error>|did you mean")
    hit = False
    for l in err_lines:
        if "error:" not in l:
            continue
        m = member.search(l)
        if m:
            name = next(g for g in m.groups() if g)
            if name in pending_ops:
                hit = True
                continue
            return False  # schema 成员错误但不是本次新增的算子名——疑似拼写错误，真 FAIL
        if cascade.search(l):
            continue
        return False  # 存在与 schema 生成无关的独立错误
    return hit

def extract(e):
    cmd = shlex.split(e["command"]) if "command" in e else list(e["arguments"])
    comp, out, skip = cmd[0], [], False
    for t in cmd[1:]:
        if skip:
            skip = False
            continue
        if t in ("-o", "-c", "-MF", "-MT", "-MQ"):
            skip = True
            continue
        if t in ("-MD", "-MMD") or t.endswith((".c", ".cc", ".cpp", ".o")):
            continue
        out.append(t)
    return comp, out

npass = nfail = nunver = npend = 0
for f in files:
    af = os.path.abspath(f)
    if not os.path.isfile(af):
        print(f"[SKIP] {f} （文件不存在）")
        continue
    e = by_file.get(af) or by_dir.get((os.path.dirname(af), os.path.splitext(af)[1]))
    if e is None:
        print(f"[UNVERIFIED] {f} （compile_commands 无本文件及同目录兄弟条目——交给真实构建）")
        nunver += 1
        continue
    comp, flags = extract(e)
    # 与真实构建对齐之外再兜两类实证踩过的坑（重复给出无害）
    argv = [comp, "-fsyntax-only", "-Werror=narrowing", "-Werror=return-type", *flags, af]
    try:
        r = subprocess.run(argv, capture_output=True, text=True,
                           cwd=e.get("directory", "."), timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as ex:
        print(f"[UNVERIFIED] {f} （预检编译器不可用/超时: {ex}）")
        nunver += 1
        continue
    if r.returncode == 0:
        print(f"[PASS] {f}")
        npass += 1
        continue
    err = (r.stderr or r.stdout).splitlines()
    key = [l for l in err if "error:" in l or "warning:" in l] or err
    if any("No such file or directory" in l and "fatal error" in l for l in err) \
       and not any("error:" in l and "No such file or directory" not in l for l in err):
        print(f"[UNVERIFIED] {f} （新引入的头在该 target include 路径外——真实构建大概率同样失败，先核对 include 与 CMake 源列表）")
        for l in key[:3]:
            print("    " + l)
        nunver += 1
        continue
    if schema_pending(err):
        print(f"[SCHEMA_PENDING] {f} （仅缺 schema 生成类型——XxxT/PrimitiveType_Xxx/value_as_Xxx "
              f"由构建期 schema_gen+flatc 自动生成，不阻塞构建；除此之外无其它错误）")
        npend += 1
        continue
    print(f"[FAIL] {f}：")
    for l in key[:12]:
        print("    " + l)
    nfail += 1

print("=" * 50)
print(f"预检结果（compile_commands 模式）：PASS={npass} FAIL={nfail} "
      f"SCHEMA_PENDING={npend} UNVERIFIED={nunver}")
if nfail:
    print("[!] 存在 FAIL——逐条修复后重跑本脚本直至 FAIL=0，再启动 build_mslite.sh")
    sys.exit(1)
print("预检通过（SCHEMA_PENDING / UNVERIFIED 不阻塞），可启动 build_mslite.sh")
PYEOF
  RC=$?
  if [ ${LINT_FAIL} -gt 0 ]; then
    echo "[!] 另有头文件 lint FAIL=${LINT_FAIL}（extern \"C\" 守卫，见上方）——同样修复后才许构建"
    exit 1
  fi
  exit ${RC}
fi

# ---- 降级：无 compile_commands（尚未构建过）——手拼 include 集 ----
# 纯 C（nnacl_c）头依赖浅可定案；C++ 头依赖深、手拼不可靠，只报 UNVERIFIED 不误伤。
echo "[i] 未找到 compile_commands.json（尚无构建记录）——降级为手拼 include 集：.c 可定案，.cc 仅供参考"
INC=()
for d in . .. src src/litert src/litert/kernel/cpu src/common include \
         tools tools/converter tools/converter/micro tools/converter/micro/coder \
         ../mindspore/mindspore ../mindspore/mindspore/ops \
         ../mindspore/mindspore/core ../mindspore/mindspore/core/include; do
  [ -d "${d}" ] && INC+=("-I${d}")
done
CC_BIN="${CC:-gcc}"
CXX_BIN="${CXX:-g++}"
pass=0; fail=0; unver=0
for f in "${FILES[@]}"; do
  if [ ! -f "${f}" ]; then echo "[SKIP] ${f} （文件不存在）"; continue; fi
  case "${f}" in
    *.cc) cmd=("${CXX_BIN}" -std=c++17); is_cc=1 ;;
    *.c)  cmd=("${CC_BIN}" -std=c11);    is_cc=0 ;;
    *)    continue ;;
  esac
  out=$("${cmd[@]}" -fsyntax-only -Wall -Werror=narrowing -Werror=return-type \
        "${INC[@]}" "${f}" 2>&1)
  rc=$?
  if [ ${rc} -eq 0 ]; then
    echo "[PASS] ${f}"
    pass=$((pass+1)); continue
  fi
  if [ ${is_cc} -eq 1 ] || { printf '%s' "${out}" | grep -q "fatal error: .*No such file or directory" \
       && ! printf '%s' "${out}" | grep -v "No such file or directory" | grep -q "error:"; }; then
    echo "[UNVERIFIED] ${f} （降级模式无法定案——交给真实构建，构建失败时优先怀疑本文件）"
    printf '%s\n' "${out}" | grep -E "fatal error|error:" | head -3 | sed 's/^/    /'
    unver=$((unver+1)); continue
  fi
  echo "[FAIL] ${f}："
  printf '%s\n' "${out}" | grep -E "error:|warning:" | head -12 | sed 's/^/    /'
  fail=$((fail+1))
done
echo "=================================================="
echo "预检结果（降级模式）：PASS=${pass} FAIL=${fail} 头文件lint FAIL=${LINT_FAIL} UNVERIFIED=${unver}"
if [ $((fail + LINT_FAIL)) -gt 0 ]; then
  echo "[!] 存在 FAIL——逐条修复后重跑本脚本直至 FAIL=0，再启动 build_mslite.sh"
  exit 1
fi
echo "预检通过（UNVERIFIED 不阻塞），可启动 build_mslite.sh"
