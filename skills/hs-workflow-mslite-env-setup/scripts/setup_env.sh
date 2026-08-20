#!/bin/bash
# MindSpore Lite 环境变量设置脚本（通用版）
# 用法: source setup_env.sh
#
# 设计原则（让它对任何用户/机器都能用）:
#   1. 优先级 = 用户预设(环境变量) > ~/.hispark_env > 自动探测 > 失败并给修复指引
#   2. 路径用 glob 匹配，不写死目录名/版本号
#   3. 项目根靠"向上找 src/mindspore-lite 标志目录"探测，不依赖 skill 装在哪
#   4. 关键路径全部校验存在性；缺失即 fail-fast，一次性报全所有问题
#   5. sourced 脚本不用 set -e（避免污染调用方 shell），用累加错误 + 末尾 return/exit
#
# 每台机器必然不同的两件事（项目根、毕昇工具链位置）可写进 ~/.hispark_env，例如:
#   export HISPARK_AI_ROOT=/path/to/hispark_ai
#   export BISHENG_ROOT=/path/to/BiSheng-llvm-xxx

# ---- 错误累加（不 set -e，一次报全）-----------------------------------------
_ERRORS=0
_err() { echo "  ✗ $*" >&2; _ERRORS=$((_ERRORS + 1)); }
_warn() { echo "  ⚠ $*" >&2; }   # 告警但不计入 _ERRORS、不阻断（仅个别步骤需要的可选依赖用）
_ok()  { echo "  ✓ $*"; }
_src() { echo "  · $*"; }

echo "[setup_env] 配置 MindSpore Lite 环境"

# ---- 0. 每机器配置文件（用户在此覆盖一切）-----------------------------------
if [ -z "${HISPARK_AI_ROOT:-}" ] && [ -f "$HOME/.hispark_env" ]; then
  _src "加载 $HOME/.hispark_env"
  source "$HOME/.hispark_env"
fi

# ---- 1. HISPARK_AI_ROOT（尊重预设 > 向上找 src/mindspore-lite）--------------
if [ -z "${HISPARK_AI_ROOT:-}" ]; then
  _d="$PWD"
  while [ "$_d" != "/" ]; do
    if [ -d "$_d/src/mindspore-lite" ]; then HISPARK_AI_ROOT="$_d"; break; fi
    _d="$(dirname "$_d")"
  done
  [ -n "${HISPARK_AI_ROOT:-}" ] && _src "自动探测 HISPARK_AI_ROOT（从 $PWD 向上找 src/mindspore-lite）"
else
  _src "使用预设 HISPARK_AI_ROOT"
fi
if [ -z "${HISPARK_AI_ROOT:-}" ] || [ ! -d "$HISPARK_AI_ROOT/src/mindspore-lite" ]; then
  _err "未定位到 HiSpark.AI 项目根（找不到 src/mindspore-lite 标志目录）。
        修复: export HISPARK_AI_ROOT=<你的 hispark_ai 路径>，或在该路径下 source 本脚本，或写入 ~/.hispark_env"
else
  export HISPARK_AI_ROOT
  _ok "HISPARK_AI_ROOT = $HISPARK_AI_ROOT"
fi

# ---- 2. BISHENG_ROOT（尊重预设 > 项目树内 glob > 失败）----------------------
# 毕昇编译器是独立下载的，可能在项目树内、也可能在别处，故只在不冲突时 glob 项目树。
if [ -z "${BISHENG_ROOT:-}" ] && [ -n "${HISPARK_AI_ROOT:-}" ]; then
  _hit="$(ls -d "$HISPARK_AI_ROOT"/BiSheng-llvm-* 2>/dev/null | head -1)"
  [ -n "$_hit" ] && { BISHENG_ROOT="$_hit"; _src "自动探测 BISHENG_ROOT（项目树内 glob）"; }
else
  [ -n "${BISHENG_ROOT:-}" ] && _src "使用预设 BISHENG_ROOT"
fi
if [ -z "${BISHENG_ROOT:-}" ] || [ ! -x "$BISHENG_ROOT/bin/clang" ]; then
  _err "未找到毕昇 RISC-V 工具链（需含 bin/clang）。
        修复: 从华为开发者官网 https://developers.hisilicon.com/cn/developerTool 下载
              BiSheng-llvm-15.0.4-riscv-x86-linux（资源下载→Toolchain→Linux→RISC-V），
              tar -xzvf 解压后 export BISHENG_ROOT=<解压目录>，
              或解压到项目根/写入 ~/.hispark_env。详见 references/faq.md「获取毕昇编译器」。"
else
  export BISHENG_ROOT
  _ok "BISHENG_ROOT = $BISHENG_ROOT"
fi

# ---- 2b. ARM musl GCC 工具链（HISPARK_ARM_TOOLCHAIN_PATH）------------------
# 与毕昇并列的第二条交叉工具链。优先用官方 install_gcc_toolchain.sh 装到
# /opt/linux/x86-arm/<name>/；也可在项目树内解压。解压布局是嵌套的：
#   gcc-10.3-arm-musl-x86-linux-<ver>/arm-v01c01-linux-musleabi-gcc/bin/arm-v01c01-linux-musleabi-gcc
# 故“工具链根”= 含 bin/arm-v01c01-linux-musleabi-gcc 的那一层，而非最外层目录。
_ARM_GCC="arm-v01c01-linux-musleabi-gcc"
if [ -z "${ARM_TOOLCHAIN_ROOT:-}" ]; then
  _found=""
  for _cand in "/opt/linux/x86-arm/arm-v01c01-linux-musleabi-gcc"; do
    [ -x "$_cand/bin/$_ARM_GCC" ] && { _found="$_cand"; break; }
  done
  if [ -z "$_found" ] && [ -n "${HISPARK_AI_ROOT:-}" ]; then
    for _cand in "$HISPARK_AI_ROOT"/gcc-10.3-arm-musl-*/arm-v01c01-linux-musleabi-gcc; do
      [ -x "$_cand/bin/$_ARM_GCC" ] && { _found="$_cand"; break; }
    done
  fi
  [ -n "$_found" ] && { ARM_TOOLCHAIN_ROOT="$_found"; _src "自动探测 ARM_TOOLCHAIN_ROOT"; }
else
  _src "使用预设 ARM_TOOLCHAIN_ROOT"
fi
if [ -z "${ARM_TOOLCHAIN_ROOT:-}" ] || [ ! -x "$ARM_TOOLCHAIN_ROOT/bin/$_ARM_GCC" ]; then
  _warn "未找到 ARM musl GCC 工具链（需含 bin/$_ARM_GCC）—— 仅“编译 mslite 框架”（build_mslite.sh）需要；
        转换模型 / 构建 RISC-V 静态库等步骤不受影响，本脚本继续。
        需要编译时: 从华为开发者官网 https://developers.hisilicon.com/cn/developerTool 下载
        gcc-10.3-arm-musl-x86-linux，tar -xzvf 解压后 sudo ./install_gcc_toolchain.sh（默认装 /opt/linux/x86-arm），
        或 export ARM_TOOLCHAIN_ROOT=<.../arm-v01c01-linux-musleabi-gcc> / 写入 ~/.hispark_env。
        详见 references/faq.md「获取 ARM GCC 工具链」。"
else
  export ARM_TOOLCHAIN_ROOT
  export HISPARK_ARM_TOOLCHAIN_PATH="$ARM_TOOLCHAIN_ROOT"
  _ok "HISPARK_ARM_TOOLCHAIN_PATH = $ARM_TOOLCHAIN_ROOT"
fi

# ---- 3. MSLITE_PKG（预设目录存在才采纳 > 否则 glob 自动探测任意版本）---------
# MSLITE_PKG 是编译产物，版本号随迭代变化；上游会话可能注入过期预设值，
# 故仅当预设目录真实存在时才采纳，否则一律回退 glob 自动探测，避免版本锁死。
if [ -n "${MSLITE_PKG:-}" ] && [ -d "$MSLITE_PKG" ]; then
  _src "使用预设 MSLITE_PKG（目录存在）"
elif [ -n "${HISPARK_AI_ROOT:-}" ]; then
  _hit="$(ls -d "$HISPARK_AI_ROOT"/src/mindspore-lite/output/mindspore-lite-*-linux-x64 2>/dev/null | head -1)"
  if [ -n "$_hit" ]; then
    MSLITE_PKG="$_hit"
    _src "自动探测 MSLITE_PKG（glob 任意版本）"
  else
    unset MSLITE_PKG
  fi
fi
if [ -n "${MSLITE_PKG:-}" ] && [ -d "$MSLITE_PKG" ]; then
  export MSLITE_PKG
  _ok "MSLITE_PKG = $MSLITE_PKG"
else
  _src "暂无已编译的 MSLite 产物目录（mindspore-lite-*-linux-x64）—— 编译前属正常。
        需转换模型/构建静态库时先跑 build_mslite.sh，或 export MSLITE_PKG=<产物目录>"
fi

# ---- 4. MSLite 编译选项（常量，无外部依赖）----------------------------------
export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_TARGET_RISCV=ON
[ -n "${BISHENG_ROOT:-}" ] && export HISPARK_RISCV_TOOLCHAIN_PATH="$BISHENG_ROOT"

# ---- 5. Python（动态查找 3.11+，不写死路径）---------------------------------
_py=""
for _c in python3.11 python3.12 python3.13 python3.14; do
  _p="$(command -v "$_c" 2>/dev/null)" && { _py="$_p"; break; }
done
if [ -n "$_py" ]; then
  export CMAKE_ARGS="-DPython3_EXECUTABLE=$_py"
  _ok "CMAKE_ARGS Python = $_py"
else
  _err "未找到 python3.11+（CMAKE 需要）。修复: 安装 Python 3.11 或设 CMAKE_ARGS"
fi

# ---- 6. PATH / LD_LIBRARY_PATH（让 converter_lite 直接可用）------------------
if [ -n "${MSLITE_PKG:-}" ] && [ -d "$MSLITE_PKG" ]; then
  case ":$PATH:" in
    *":$MSLITE_PKG/tools/converter/converter:"*) ;;
    *) export PATH="$MSLITE_PKG/tools/converter/converter:$PATH" ;;
  esac
  _setup_script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
  if source "$_setup_script_dir/converter_runtime_env.sh"; then
    _ok "converter_lite 已加入 PATH；动态库已从本轮 MSLITE_PKG 自动配置"
  else
    _err "本轮 MSLITE_PKG 缺少 converter 运行库，不能启动 converter_lite"
  fi
  unset _setup_script_dir
fi

# ---- 7. 毕昇 riscv32-linux-musl-gcc 软链接（先校验布局再建）------------------
if [ -n "${BISHENG_ROOT:-}" ] && [ -x "$BISHENG_ROOT/bin/clang" ]; then
  GCC_LINK="$BISHENG_ROOT/bin/riscv32/riscv32-linux-musl-gcc"
  GXX_LINK="$BISHENG_ROOT/bin/riscv32/riscv32-linux-musl-g++"
  if [ ! -e "$GCC_LINK" ]; then
    _src "创建软链接: clang -> riscv32-linux-musl-gcc"
    mkdir -p "$BISHENG_ROOT/bin/riscv32"
    ln -sf "$BISHENG_ROOT/bin/clang"  "$GCC_LINK"
    ln -sf "$BISHENG_ROOT/bin/clang++" "$GXX_LINK"
  fi
  # 交叉编译器实测（失败不再静默）
  # 用 mktemp -d 创建私有临时目录(随机名+700权限+原子创建), 避免固定 /tmp 路径的
  # symlink 攻击(TOCTOU)与多用户并发冲突; 三个临时文件放入该目录, 末尾整目录清理。
  _test_dir=$(mktemp -d)
  _test_c="$_test_dir/test.c"
  _test_o="$_test_dir/test.o"
  _test_err="$_test_dir/err"
  echo 'int main(){return 0;}' > "$_test_c"
  if "$GCC_LINK" -march=rv32imafc -mabi=ilp32f -c "$_test_c" -o "$_test_o" 2>"$_test_err"; then
    _ok "RISC-V 交叉编译器验证通过"
  else
    _err "RISC-V 交叉编译器验证失败: $(cat "$_test_err" 2>/dev/null)"
  fi
  rm -rf "$_test_dir"
fi

# ---- 7b. ARM 交叉编译器实测（gcc 自带 musl sysroot，无需 --sysroot）---------
if [ -n "${ARM_TOOLCHAIN_ROOT:-}" ] && [ -x "$ARM_TOOLCHAIN_ROOT/bin/$_ARM_GCC" ]; then
  _test_dir=$(mktemp -d)
  echo 'int main(){return 0;}' > "$_test_dir/t.c"
  if "$ARM_TOOLCHAIN_ROOT/bin/$_ARM_GCC" -c "$_test_dir/t.c" -o "$_test_dir/t.o" 2>"$_test_dir/err"; then
    _ok "ARM 交叉编译器验证通过"
  else
    _err "ARM 交叉编译器验证失败: $(cat "$_test_dir/err" 2>/dev/null)"
  fi
  rm -rf "$_test_dir"
fi

# ---- 8. 汇总 ---------------------------------------------------------------
if [ "$_ERRORS" -gt 0 ]; then
  echo "[setup_env] ✗ 失败：$_ERRORS 项缺失，请按上述提示修复后重试。" >&2
  return 1 2>/dev/null || exit 1
fi
echo "[setup_env] ✓ 环境就绪。后续可运行: build_mslite.sh / convert_model.sh / build_static_lib.sh"
