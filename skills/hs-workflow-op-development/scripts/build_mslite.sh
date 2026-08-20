#!/bin/bash
# Copyright 2026 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# build_mslite.sh --run-id <id> [--full] [构建根目录]  启动一次可追踪构建
# build_mslite.sh --wait [max_secs] <id>    只等待指定构建轮次
# build_mslite.sh --status <id>             只报告指定构建轮次
# build_mslite.sh --stop                    终止当前构建（杀整个进程组，含 make/编译器子进程）
#
# hs-workflow-op-development stage3 标准工具包重建入口，一条命令完成：
#   并发锁（同一时刻只允许一个构建）→ 固定 env 开关 → 定位 RISC-V 工具链
#   → bash build.sh（默认增量 -i，--full 全量）→ 断言交叉库产出 → 解压产物
#   → 断言改动的 parser 注册符号已真正链入产物（堵「假编译成功」，exit 6）→ 打印 MSLITE_PKG
# 失败即非零退出并说明原因。不要绕过本脚本直接跑 build.sh / make——裸跑丢 env、
# 产物配置错误（编译失败修复后的重跑同样只经本脚本）。
#
# 启动（后台运行，编译 10–30 分钟；日志由脚本自写到状态目录，调用方无需另定日志名；
# status 同时校验 RUN_ID、日志头、RC 与源码指纹，不会读取上一轮结果冒充本轮）：
#   OP_BUILD_RUN_ID="op-$(date +%Y%m%d%H%M%S)-$$"
#   nohup bash <skill>/scripts/build_mslite.sh --run-id "$OP_BUILD_RUN_ID" [构建根目录] >/dev/null 2>&1 &
# 跟踪进度的推荐方式——一条命令内部轮询到结束或到时（杜绝调用方 sleep 算术；
# 调用方把 Bash 工具 timeout 设为 (max_secs+60)秒 对应毫秒数，如 --wait 540 配 timeout 600000）：
#   bash <skill>/scripts/build_mslite.sh --wait 540 "$OP_BUILD_RUN_ID"
# 返回 0=SUCCESS、1=FAILED、10=到时仍在构建（再跑一次 --wait 接着等即可）。
# 也可 --status 即时查看（RUNNING 则 sleep 60 后重查；单次 sleep ≤110 秒——更长会被
# Bash 工具默认 120s 超时杀掉，exit 143 是 sleep 被杀不是构建结果）：
#   bash <skill>/scripts/build_mslite.sh --status "$OP_BUILD_RUN_ID"
# 禁止 `wait <PID>`：每次工具调用是新 shell，构建进程不是它的子进程，wait 必返 127
# （含义是"非本 shell 子进程"，不是构建结果）。
# 构建运行期间禁止编辑仓库源码或再起构建；要改代码先 `build_mslite.sh --stop`——
# 裸 kill 只杀外层脚本，孤儿 make 继续跑，会与下一轮构建互踩污染 build/。
set -u

STATE_DIR="${MSLITE_BUILD_STATE_DIR:-/tmp}"
PIDFILE="${STATE_DIR}/mslite_build.pid"
RCFILE="${STATE_DIR}/mslite_build.rc"
LOGFILE="${STATE_DIR}/mslite_build.log"
PGIDFILE="${STATE_DIR}/mslite_build.pgid"   # setsid 后的构建进程组组长，--stop 据此整组清场
STARTFILE="${STATE_DIR}/mslite_build.start" # RUN_ID/start/root/source fingerprint
RUNIDFILE="${STATE_DIR}/mslite_build.run_id"

mkdir -p "${STATE_DIR}"

read_meta() {
  META_RUN_ID=""; META_STARTED=""; META_ROOT=""; META_FINGERPRINT=""
  [ -f "${STARTFILE}" ] || return 1
  while IFS='=' read -r key value; do
    case "${key}" in
      RUN_ID) META_RUN_ID="${value}" ;;
      STARTED) META_STARTED="${value}" ;;
      ROOT) META_ROOT="${value}" ;;
      SOURCE_FINGERPRINT) META_FINGERPRINT="${value}" ;;
    esac
  done < "${STARTFILE}"
  [ -n "${META_RUN_ID}" ] && [ -n "${META_ROOT}" ]
}

fingerprint_repo() {
  local repo="$1" label="$2"
  # Fingerprinting must inspect the bytes already present in the worktree.  Do
  # not invoke Git LFS clean filters here: large dirty submodules can otherwise
  # block before STARTFILE is published and leave no diagnosable build record.
  local -a git_no_filters=(git -c filter.lfs.process= -c filter.lfs.clean=cat -c filter.lfs.required=false)
  echo "${label}:HEAD=$(git -C "${repo}" rev-parse HEAD 2>/dev/null || echo NO_HEAD)"

  # The nested MindSpore repository is a pinned build dependency.  Its Windows
  # checkout may appear wholly dirty because of line-ending conversion, making
  # even a metadata-only diff take many minutes.  The outer repository (where
  # Lite operator sources live) is still fingerprinted byte-for-byte below;
  # direct submodules are identified by their immutable commit SHA here.
  if [[ "${label}" == SUBMODULE:* ]]; then
    return 0
  fi

  # Raw metadata preserves status, object IDs and mode changes without materializing
  # a potentially enormous binary patch for line-ending-dirty repositories.
  "${git_no_filters[@]}" -C "${repo}" diff --ignore-submodules=dirty --no-ext-diff --no-textconv --raw --no-abbrev -z HEAD -- 2>/dev/null
  echo "${label}:TRACKED_CONTENT"
  "${git_no_filters[@]}" -C "${repo}" diff --ignore-submodules=dirty --no-ext-diff --no-textconv --name-only -z HEAD -- 2>/dev/null |
    while IFS= read -r -d '' rel; do
      [ -f "${repo}/${rel}" ] || [ -L "${repo}/${rel}" ] || continue
      printf '%s\0' "${repo}/${rel}"
    done | if [[ "${label}" == SUBMODULE:* ]]; then
      # Windows checkouts can report an entire nested repository dirty only
      # because of line-ending conversion.  Hashing every byte makes startup
      # take many minutes.  Size + nanosecond mtime still invalidates an active
      # build when any such worktree file is edited, while the parent gitlink
      # and raw diff above preserve repository identity.
      xargs -0 -r stat -c 'TRACKED:%s:%Y:%y:%n' -- 2>/dev/null
    else
      xargs -0 -r sha256sum -- 2>/dev/null
    fi

  echo "${label}:UNTRACKED_NAMES"
  git -C "${repo}" ls-files --others --exclude-standard -z 2>/dev/null
  echo "${label}:UNTRACKED_CONTENT"
  git -C "${repo}" ls-files --others --exclude-standard -z 2>/dev/null |
    while IFS= read -r -d '' rel; do printf '%s\0' "${repo}/${rel}"; done |
    xargs -0 -r sha256sum -- 2>/dev/null
  git -C "${repo}" ls-files --others --exclude-standard -z 2>/dev/null |
    while IFS= read -r -d '' rel; do printf '%s\0' "${repo}/${rel}"; done |
    xargs -0 -r stat -c 'MODE:%a:%n' -- 2>/dev/null
}

source_fingerprint() {
  local root="$1" repo rel
  {
    if ! git -C "${root}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      echo NO_GIT_REPOSITORY
      return
    fi
    fingerprint_repo "${root}" ROOT

    # Hash direct build dependencies in full. Do not recursively enter nested
    # test/model submodules: their gitlink/dirty metadata is already captured
    # by the direct parent's raw diff, while content-walking them can delay a
    # converter build for hours on a line-ending-dirty Windows worktree.
    while read -r rel; do
      [ -n "${rel}" ] || continue
      repo="${root}/${rel}"
      fingerprint_repo "${repo}" "SUBMODULE:${rel}"
    done < <(git -C "${root}" submodule status 2>/dev/null | awk '{print $2}')
  } | sha256sum | awk '{print $1}'
}

# ---- --status：即时返回，不阻塞 ----
if [ "${1:-}" = "--status" ]; then
  EXPECTED_RUN_ID="${2:-}"
  CURRENT_RUN_ID=$(cat "${RUNIDFILE}" 2>/dev/null || true)
  if [ -z "${EXPECTED_RUN_ID}" ]; then
    if [ -f "${PIDFILE}" ] && kill -0 "$(cat "${PIDFILE}")" 2>/dev/null; then
      EXPECTED_RUN_ID="${CURRENT_RUN_ID}"
    else
      echo "NO_CURRENT_BUILD：没有运行中的构建；其他运行结果只能带 RUN_ID 显式查询，不能作为本轮结论。"
      [ -n "${CURRENT_RUN_ID}" ] && echo "HISTORICAL_RUN_ID=${CURRENT_RUN_ID}"
      exit 12
    fi
  fi
  if [ -z "${CURRENT_RUN_ID}" ] || [ "${EXPECTED_RUN_ID}" != "${CURRENT_RUN_ID}" ]; then
    echo "STALE_BUILD_RECORD：请求 RUN_ID=${EXPECTED_RUN_ID}，当前记录 RUN_ID=${CURRENT_RUN_ID:-NONE}；禁止读取别轮日志/RC。"
    exit 12
  fi
  if ! read_meta || [ "${META_RUN_ID}" != "${EXPECTED_RUN_ID}" ] \
      || ! head -1 "${LOGFILE}" 2>/dev/null | grep -qF "RUN_ID=${EXPECTED_RUN_ID}"; then
    echo "STALE_BUILD_RECORD：RUN_ID、启动元数据与日志头不一致；该记录不能作为当前构建结果。"
    exit 12
  fi
  if [ -f "${PIDFILE}" ] && kill -0 "$(cat "${PIDFILE}")" 2>/dev/null; then
    CURRENT_FINGERPRINT=$(source_fingerprint "${META_ROOT}")
    if [ "${CURRENT_FINGERPRINT}" != "${META_FINGERPRINT}" ]; then
      echo "STALE_BUILD_RECORD：RUN_ID=${EXPECTED_RUN_ID} 运行中源码内容已变化；先 --stop，再启动新构建。"
      exit 12
    fi
    el=""
    if [ -n "${META_STARTED}" ]; then
      _now=$(date +%s); _start="${META_STARTED}"
      el="，已运行 $(( (_now - _start) / 60 ))m$(( (_now - _start) % 60 ))s"
    fi
    echo "RUNNING (RUN_ID=${EXPECTED_RUN_ID} PID=$(cat "${PIDFILE}")${el})——本轮日志尾部："
    tail -5 "${LOGFILE}" 2>/dev/null
    echo "[i] 推荐 \`--wait 540\`（Bash 工具 timeout 设 600000）一条命令等到结束；用 --status 轮询则 sleep 60 后重查（单次 sleep ≤110s，更长会被工具超时杀掉）。构建期间禁止编辑源码/再起构建；要中止改代码用 --stop"
    exit 10
  fi
  if [ ! -f "${RCFILE}" ]; then
    echo "INCOMPLETE_BUILD_RECORD：RUN_ID=${EXPECTED_RUN_ID} 的进程已退出但本轮 RC 尚未写入；禁止回退读取其他运行的 RC。"
    exit 12
  fi
  read -r RC_RUN_ID rc < "${RCFILE}"
  if [ "${RC_RUN_ID:-}" != "${EXPECTED_RUN_ID}" ] || [ -z "${rc:-}" ]; then
    echo "STALE_BUILD_RECORD：RC 属于 RUN_ID=${RC_RUN_ID:-UNKNOWN}，不是请求的 ${EXPECTED_RUN_ID}。"
    exit 12
  fi
  if [ "${rc}" = "7" ]; then
    echo "SUBMOD-DRIFT (exit 7)：build.sh 把子模块推进到未测试的 commit——这不是算子缺陷，禁止改代码。"
    grep -n "\[SUBMOD-LOCK\]" "${LOGFILE}" 2>/dev/null
    echo "[i] 按上面的恢复步骤把子模块 checkout 回构建前 SHA、注释 build.sh 的 update_submodule 后重建。"
    exit 7
  fi
  CURRENT_FINGERPRINT=$(source_fingerprint "${META_ROOT}")
  if [ "${CURRENT_FINGERPRINT}" != "${META_FINGERPRINT}" ]; then
    echo "STALE_BUILD_RECORD：RUN_ID=${EXPECTED_RUN_ID} 启动后源码内容已变化，旧 RC/日志不能作为当前结论；必须启动新构建。"
    exit 12
  fi
  if [ "${rc}" = "0" ]; then
    echo "SUCCESS：RUN_ID=${EXPECTED_RUN_ID} 本轮构建成功。"
    grep "MSLITE_PKG=" "${LOGFILE}" 2>/dev/null | tail -1
    exit 0
  fi
  echo "FAILED (exit ${rc})——错误摘要："
  grep -n "error:" "${LOGFILE}" 2>/dev/null | head -15
  # 链接失败的关键信息（undefined reference 等）不含 "error:"，必须单独提取——
  # 修复动作只能基于下面的符号名与失败 target；没拿到符号名前禁止清缓存/全量重建
  # （见 <hs-dev-op-implement>/references/troubleshooting.md 链接条目）
  if grep -q "ld returned 1 exit status" "${LOGFILE}" 2>/dev/null; then
    echo "[链接失败] undefined/缺库明细（去重）："
    grep -ohE "undefined reference to [^,;]*|cannot find -l[A-Za-z0-9_.-]+|multiple definition of [^,;]*" "${LOGFILE}" 2>/dev/null | sort -u | head -20
    echo "[链接失败] 失败的链接 target："
    grep -nE "Linking (C|CXX) (executable|shared library|static library)" "${LOGFILE}" 2>/dev/null | tail -3
    grep -nE "make(\[[0-9]+\])?: \*\*\*.*Error [0-9]+" "${LOGFILE}" 2>/dev/null | tail -3
  fi
  if grep -q "\[REG-ASSERT\]" "${LOGFILE}" 2>/dev/null; then
    echo "[假编译拦截] 改算子加了 parser 却没链进 .so（注册符号 dead-strip）——详情："
    grep -n "\[REG-ASSERT\]" "${LOGFILE}" 2>/dev/null
  fi
  if grep -qE "Killed|internal compiler error|cc1plus.*[Kk]illed" "${LOGFILE}" 2>/dev/null; then
    echo "[i] 疑似 OOM：用 JOBS=<当前值的一半> 重跑本脚本"
  fi
  echo "[i] 分诊：报错文件不是本次会话创建/修改的（git status/diff 佐证）→ 预存问题，停下报告用户；"
  echo "    是本次改动 → 最小改动修复（禁止删功能换编译通过），仍经本脚本重跑"
  exit 1
fi

# ---- --wait [max_secs]：阻塞等待构建结束（内部轮询，默认 540s）----
# 一条命令替代"sleep N && --status"的人肉轮询循环——后者要求调用方算 sleep 上限，
# 实证多次算错（sleep 600 被工具 120s 默认超时杀掉、exit 143 被误读为构建结果）。
# 调用方唯一要做的：Bash 工具 timeout 给足 (max_secs+60)*1000 毫秒。
if [ "${1:-}" = "--wait" ]; then
  MAX="${2:-540}"
  EXPECTED_RUN_ID="${3:-}"
  case "${MAX}" in (*[!0-9]*|"") echo "[!] --wait 的上限须为秒数，如 --wait 540" >&2; exit 1;; esac
  if [ -z "${EXPECTED_RUN_ID}" ]; then
    echo "[!] --wait 必须携带启动时保存的 RUN_ID，避免把其他构建当成本轮结果。" >&2
    exit 12
  fi
  # nohup 启动与下一次工具调用之间存在短竞态：wait 可能先读到上一轮 RUNIDFILE。
  # 给新 wrapper 最多 15 秒发布本轮 identity；仍未出现则再按 status 的陈旧记录分流。
  startup_waited=0
  while [ "$(cat "${RUNIDFILE}" 2>/dev/null || true)" != "${EXPECTED_RUN_ID}" ] \
      && [ "${startup_waited}" -lt 15 ]; do
    sleep 1
    startup_waited=$((startup_waited + 1))
  done
  waited=0
  while [ -f "${PIDFILE}" ] && kill -0 "$(cat "${PIDFILE}")" 2>/dev/null; do
    if [ "${waited}" -ge "${MAX}" ]; then
      "$0" --status "${EXPECTED_RUN_ID}"
      echo "[i] --wait 达到上限 ${MAX}s，构建仍在进行——再跑一次 --wait 接着等（不要 --stop，不要另起构建）"
      exit 10
    fi
    sleep 15
    waited=$((waited + 15))
  done
  exec "$0" --status "${EXPECTED_RUN_ID}"
fi

# ---- --stop：终止整个构建进程组（含 make/编译器子进程），改代码前用 ----
if [ "${1:-}" = "--stop" ]; then
  if ! { [ -f "${PIDFILE}" ] && kill -0 "$(cat "${PIDFILE}")" 2>/dev/null; }; then
    echo "NO_BUILD：无运行中的构建，无需停止"
    exit 0
  fi
  wrapper="$(cat "${PIDFILE}")"
  build_pg="$(cat "${PGIDFILE}" 2>/dev/null || true)"
  wrapper_pg="$(ps -o pgid= -p "${wrapper}" 2>/dev/null | tr -d ' ')"
  stopper_pg="$(ps -o pgid= -p $$ 2>/dev/null | tr -d ' ')"
  [ -n "${build_pg}" ] && kill -TERM -- "-${build_pg}" 2>/dev/null
  if [ -n "${wrapper_pg}" ] && [ "${wrapper_pg}" != "${stopper_pg}" ]; then
    kill -TERM -- "-${wrapper_pg}" 2>/dev/null
  else
    kill -TERM "${wrapper}" 2>/dev/null
  fi
  for _ in 1 2 3 4 5; do kill -0 "${wrapper}" 2>/dev/null || break; sleep 1; done
  [ -n "${build_pg}" ] && kill -KILL -- "-${build_pg}" 2>/dev/null
  if [ -n "${wrapper_pg}" ] && [ "${wrapper_pg}" != "${stopper_pg}" ]; then
    kill -KILL -- "-${wrapper_pg}" 2>/dev/null
  fi
  kill -KILL "${wrapper}" 2>/dev/null
  rm -f "${PIDFILE}" "${PGIDFILE}"
  echo "STOPPED：构建已终止（wrapper 进程组 ${wrapper_pg:-未知}，build 进程组 ${build_pg:-未生成} 已清场）。改完代码后仍经本脚本重跑。"
  exit 0
fi

RUN_ID=""
if [ "${1:-}" = "--run-id" ]; then
  RUN_ID="${2:-}"
  [ -n "${RUN_ID}" ] || { echo "[!] --run-id 后必须给非空 ID" >&2; exit 1; }
  shift 2
fi
if [ -z "${RUN_ID}" ]; then
  echo "[!] 启动构建必须使用 --run-id <唯一ID>；workflow 后续只能查询这一轮。" >&2
  exit 1
fi
case "${RUN_ID}" in (*[!A-Za-z0-9_.-]*) echo "[!] RUN_ID 只允许字母、数字、点、下划线和连字符" >&2; exit 1;; esac

FULL=0
if [ "${1:-}" = "--full" ]; then FULL=1; shift; fi
ROOT="${1:-.}"
cd "${ROOT}" || exit 1
if [ ! -f build.sh ]; then
  echo "[!] ${PWD} 不是构建根目录（缺 build.sh）——传入含 build.sh/output/ 的目录重跑" >&2
  exit 1
fi

# ---- 并发锁：同一时刻只允许一个构建 ----
if [ -f "${PIDFILE}" ] && kill -0 "$(cat "${PIDFILE}")" 2>/dev/null; then
  echo "[!] 已有构建在运行 (PID=$(cat "${PIDFILE}"))，拒绝并发。" >&2
  echo "    要么 --status 轮询等它结束，要么 build_mslite.sh --stop 清场后重跑。" >&2
  exit 9
fi
echo $$ > "${PIDFILE}"
printf '%s\n' "${RUN_ID}" > "${RUNIDFILE}"
STARTED=$(date +%s)
SOURCE_FINGERPRINT=$(source_fingerprint "${PWD}")
{
  echo "RUN_ID=${RUN_ID}"
  echo "STARTED=${STARTED}"
  echo "ROOT=${PWD}"
  echo "SOURCE_FINGERPRINT=${SOURCE_FINGERPRINT}"
} > "${STARTFILE}"
rm -f "${RCFILE}" "${PGIDFILE}"
trap 'rc=$?; printf "%s %s\n" "${RUN_ID}" "${rc}" > "${RCFILE}.tmp"; mv "${RCFILE}.tmp" "${RCFILE}"; rm -f "${PIDFILE}" "${PGIDFILE}"' EXIT
# 自写固定日志（先截断旧内容）：--status 只认 ${LOGFILE}，与调用方是否/如何重定向无关，
# 杜绝"新一轮 RUNNING 却 tail 出上一轮 BUILD OK"的陈旧假信号
exec > "${LOGFILE}" 2>&1
echo "[build_mslite] RUN_ID=${RUN_ID} 本轮启动: $(date '+%F %T')  日志: ${LOGFILE}"

export MSLITE_ENABLE_MICRO=ON
export MSLITE_ENABLE_INT8=ON
export MSLITE_ENABLE_TRAIN=OFF
export MSLITE_ENABLE_TESTCASES=OFF
export MSLITE_TARGET_RISCV=ON
export HISPARK_SKIP_SUBMODULE_UPDATE=1

# ---- 工具链定位通用函数 ----
# 工具链 bin/ 下的入口常是符号链接（如 clang -> clang-15），
# find 必须 \( -type f -o -type l \)；只写 -type f 会永远漏掉符号链接（已实际踩过）。
# 两级策略：①按可执行名搜（f 或 l + --version 验证）；②兜底按目录名模糊搜（如 *bisheng*），再验 bin/<名>。

# ver_ok <可执行> <--version 输出须含的串(忽略大小写)>
# 必须丢弃 stderr 且要求 --version 退出码为 0：报错信息会回显含工具链名的路径
# （如 ".../BiSheng-.../bin/clang: Is a directory"），用 2>&1|grep 会把坏入口误判为通过（已实际踩过）。
ver_ok() {
  local out
  out=$("$1" --version 2>/dev/null) || return 1
  printf '%s' "${out}" | grep -qi "$2"
}

# find_toolchain <可执行名> <--version 须含的串> <目录名模糊模式>  → 输出工具链根目录
find_toolchain() {
  local exe="$1" verstr="$2" dirpat="$3" c d
  while read -r c; do
    [ -x "$c" ] || continue
    ver_ok "$c" "${verstr}" || continue
    dirname "$(dirname "$c")"; return 0
  done < <(find "${HOME}" /opt /usr/local /data -maxdepth 6 -name "${exe}" \( -type f -o -type l \) 2>/dev/null)
  while read -r d; do
    c="${d}/bin/${exe}"
    [ -x "$c" ] || continue
    ver_ok "$c" "${verstr}" || continue
    echo "$d"; return 0
  done < <(find "${HOME}" /opt /usr/local /data -maxdepth 5 -type d -iname "${dirpat}" 2>/dev/null)
  return 1
}

# ---- RISC-V 工具链（--version 含 bisheng）：尊重已设 env，否则定位 ----
if ! { [ -n "${HISPARK_RISCV_TOOLCHAIN_PATH:-}" ] \
       && [ -x "${HISPARK_RISCV_TOOLCHAIN_PATH}/bin/clang" ] \
       && ver_ok "${HISPARK_RISCV_TOOLCHAIN_PATH}/bin/clang" bisheng; }; then
  found_root=$(find_toolchain clang bisheng "*bisheng*")
  if [ -z "${found_root}" ]; then
    echo "[!] 未找到 BiSheng RISC-V 工具链——设置 HISPARK_RISCV_TOOLCHAIN_PATH 后重跑。" >&2
    echo "    人工排查（注意 bin/clang 可能是符号链接，勿用 find -type f）：" >&2
    echo "      find ~ /opt -maxdepth 5 -type d -iname '*bisheng*'" >&2
    echo "    禁止去掉 MSLITE_TARGET_RISCV 退化成 x86-only（那等于没验证）。" >&2
    exit 2
  fi
  export HISPARK_RISCV_TOOLCHAIN_PATH="${found_root}"
fi

echo "RISC-V toolchain: ${HISPARK_RISCV_TOOLCHAIN_PATH}"

# ---- 陈旧 schema 生成头自检：CMake 不追踪 ops_def.cc → ops.fbs → model_generated.h 的再生成链 ----
# ops_def.cc 改完后旧 model_generated.h 缓存仍被使用 → 编译报
# 'XxxT/PrimitiveType_Xxx is not a member of mindspore::schema' / 'has no member named value_as_Xxx'
# 且不会自愈（实证：烧掉一整轮构建才定位到）。按 mtime 机械判定，删缓存头强制 flatc 再生成。
ODC=$(ls mindspore-lite/src/common/ops/ops_def.cc src/common/ops/ops_def.cc 2>/dev/null | head -1)
for GEN in build/schema/model_generated.h build/schema/inner/model_generated.h; do
  if [ -n "${ODC}" ] && [ -f "${GEN}" ] && [ "${ODC}" -nt "${GEN}" ]; then
    echo "[i] ${ODC} 新于 ${GEN} —— 删除缓存生成头，强制 schema 再生成"
    rm -f "${GEN}"
  fi
done

# ---- JOBS：未显式给定时 = min(可用内存/1.6GB, CPU 核数)，下限 2 ----
# 1.6GB/任务是混合 C/C++ 的均值口径（converter 个别大 C++ 文件峰值更高，但同时编它们的概率低；
# 旧口径 2.5GB/任务过于保守——20 核 15GB 的机器只跑 -j5，核数利用率 1/4）。
# 真 OOM 有兜底：日志见 Killed → 按 --status 提示 JOBS=<当前值一半> 重跑。
if [ -z "${JOBS:-}" ]; then
  MEMJ=$(awk '/MemAvailable/{j=int($2/1600000); if(j<2)j=2; print j}' /proc/meminfo 2>/dev/null)
  MEMJ=${MEMJ:-4}
  CORES=$(nproc 2>/dev/null || echo 4)
  JOBS=$(( MEMJ < CORES ? MEMJ : CORES ))
fi
BUILD_ARGS="-I x86_64 -j${JOBS}"
if [ "${FULL}" -eq 0 ]; then BUILD_ARGS="${BUILD_ARGS} -i"; fi

# ---- 子模块 SHA 锁定（构建前记录）----
# build.sh 里的 update_submodule 跑 `git submodule update --init --remote`：--remote 拉的是上游
# 分支最新 commit，会把受管的 mindspore 子模块**静默推进**到一个你没测过的新 commit（非确定性）。
# 实测连锁后果（真实烧掉数小时的一次会话）：
#   ① converter 行为漂移——之前全绿的 ONNX/TFLite 用例突然成片 converter 报错，看着像算子 bug 其实不是；
#   ② 新 commit 与已 configure 的 build/ 不兼容，报 `gen_lite_ops.h: No such file or directory` 等再生成缺失；
#   ③ 失败再也无法归因到自己的改动——于是 git checkout 别的 commit、git stash、反复重建，越陷越深。
# 因此：构建前记录子模块 SHA，构建后若被推进则以 exit 7 硬停，逼你停下查环境而非改算子。
SUBMOD_DIR=""
for _c in mindspore mindspore-lite; do
  if { [ -f "${_c}/.git" ] || [ -d "${_c}/.git" ]; } && git -C "${_c}" rev-parse HEAD >/dev/null 2>&1; then
    SUBMOD_DIR="${_c}"; break
  fi
done
BEFORE_SUB_SHA=""
if [ -n "${SUBMOD_DIR}" ]; then
  BEFORE_SUB_SHA=$(git -C "${SUBMOD_DIR}" rev-parse HEAD)
  echo "[SUBMOD-LOCK] 构建前 ${SUBMOD_DIR} 子模块 HEAD: ${BEFORE_SUB_SHA}"
  PINNED_SUB_SHA=$(git ls-tree HEAD "${SUBMOD_DIR}" 2>/dev/null | awk '{print $3}')
  if [ -n "${PINNED_SUB_SHA}" ] && [ "${PINNED_SUB_SHA}" != "${BEFORE_SUB_SHA}" ]; then
    echo "[SUBMOD-LOCK] 注意：当前子模块 HEAD 与超级项目记录的 pinned SHA(${PINNED_SUB_SHA}) 不一致——"
    echo "[SUBMOD-LOCK]   子模块已偏离基线。若非你有意为之，先 git -C ${SUBMOD_DIR} checkout ${PINNED_SUB_SHA} 回到基线再构建。"
  fi
  # 若 build.sh 里 update_submodule 调用仍未注释，预警：本轮构建很可能推进子模块、结论不可复现
  if grep -Eq '^[[:space:]]*update_submodule[[:space:]]*$' build.sh 2>/dev/null; then
    echo "[SUBMOD-LOCK] 警告：build.sh 的 update_submodule 调用处于启用状态，本轮可能用 --remote 推进子模块。"
    echo "[SUBMOD-LOCK]   离线环境会因此整轮失败；联网环境会静默换 commit。构建后将自动校验是否漂移。"
  fi
fi

echo ">>> bash build.sh ${BUILD_ARGS}"
# OOM 提示：编译中出现 Killed/dumped core 多为内存不足，用 JOBS=<更小值> 重跑本脚本（每次减半）
# setsid 让 build.sh 自成进程组并记录组长 PID——--stop 据此把 make/编译器子进程一并清掉
setsid bash build.sh ${BUILD_ARGS} &
BUILD_CHILD=$!
echo "${BUILD_CHILD}" > "${PGIDFILE}"
wait "${BUILD_CHILD}"
rc=$?

# ---- 子模块漂移检测（构建后）：见上方 SUBMOD-LOCK 说明 ----
# 先于 rc 判断——子模块被推进时本轮构建对应的已不是你测试的 commit，无论编译成败都必须硬停。
if [ -n "${BEFORE_SUB_SHA}" ]; then
  AFTER_SUB_SHA=$(git -C "${SUBMOD_DIR}" rev-parse HEAD 2>/dev/null || echo "")
  if [ -n "${AFTER_SUB_SHA}" ] && [ "${AFTER_SUB_SHA}" != "${BEFORE_SUB_SHA}" ]; then
    echo "=================================================="
    echo "[SUBMOD-LOCK] error: build.sh 把 ${SUBMOD_DIR} 子模块从"
    echo "[SUBMOD-LOCK]   ${BEFORE_SUB_SHA}（构建前 / 你测试的 commit）"
    echo "[SUBMOD-LOCK] 推进到"
    echo "[SUBMOD-LOCK]   ${AFTER_SUB_SHA}（构建后 / 未经测试）"
    echo "[SUBMOD-LOCK] 成因：build.sh 的 update_submodule 跑了 \`git submodule update --init --remote\`（拉上游分支最新）。"
    echo "[SUBMOD-LOCK] 后果：converter 行为可能漂移，之前全绿的用例会成片报错——这**不是算子缺陷**。"
    echo "[SUBMOD-LOCK] 禁止据此改 parser/kernel/infer，也禁止 git checkout 别的 commit / git stash 反复试。"
    echo "[SUBMOD-LOCK] 处置（按序）："
    echo "[SUBMOD-LOCK]   ① 把子模块恢复到构建前 SHA：git -C ${SUBMOD_DIR} checkout ${BEFORE_SUB_SHA}"
    echo "[SUBMOD-LOCK]   ② 注释掉 build.sh 第一处 \`update_submodule\` 调用（保留函数定义），避免下轮再被推进"
    echo "[SUBMOD-LOCK]   ③ 经本脚本重建；④ 仍异常则把这段 SHA 漂移事实原样报告用户，停下等裁决。"
    exit 7
  fi
fi

if [ ${rc} -ne 0 ]; then
  echo "[!] 编译失败（exit ${rc}）——用 --status ${RUN_ID} 看本轮错误摘要，或在确认 RUN_ID 的日志中检索 'error:'" >&2
  exit 3
fi

# ---- RISC-V 交叉库是必须产物：缺失 = ExternalProject 静默失败 ----
# 当前 MindSpore Lite 的 MSLITE_TARGET_RISCV 只注册 nnacl_riscv ExternalProject；
# 不存在 nnacl_arm/build/arm 目标，不能用不适用的 ARM 路径误拦截成功构建。
RISCV_NNACL=build/riscv/build/nnacl/libnnacl.a
if [ ! -f "${RISCV_NNACL}" ]; then
  echo "[!] RISC-V 交叉库缺失: ${RISCV_NNACL}" >&2
  echo "    查 build/riscv/src/*-stamp/*-build-*.log；新增 nnacl_c 文件未进库时删 build/riscv 重跑" >&2
  exit 4
fi

# ---- 解压产物（hs-verify-op-host 必须用解压包，不是 build/）----
TARBALL=$(ls -t output/mindspore-lite-*-linux-x64.tar.gz output/tmp/mindspore-lite-*-linux-x64.tar.gz 2>/dev/null | head -1)
if [ -z "${TARBALL}" ]; then
  echo "[!] 未找到产物 tar.gz（output/ 或 output/tmp/ 下）" >&2
  exit 5
fi
PKG_DIR="output/$(basename "${TARBALL}" .tar.gz)"
rm -rf "${PKG_DIR}"
tar xzf "${TARBALL}" -C output/ || exit 5
if [ ! -x "${PKG_DIR}/tools/converter/converter/converter_lite" ]; then
  echo "[!] 解压后未见 converter_lite: ${PKG_DIR}" >&2
  exit 5
fi

# ---- 注册符号兜底断言：堵「假编译成功」（exit 6）----
# 失败模式：改动的 parser 经 `XxxNodeRegister g_xxx(...)` 静态初始化注册；该全局是命名空间作用域
# 外部对象，链进静态库后若无人引用，链接器会把整个对象 dead-strip——.o 编出来了、最终 .so 里却没有，
# build.sh 仍 exit 0、交叉库与产物齐备，于是「BUILD OK」是假的，真相要到 workflow Host stage 运行
# converter_lite 才暴露（报 unsupported / parse 失败，且易被误读成算子本身缺陷）。
# 这些注册全局是外部符号、存活于 .dynsym（strip 不删），可在 stripped release .so 上核验存在性。
# 据 git 改动自动发现待断言符号，无需调用方传参；发现不到注册全局（纯复用/纯 kernel/coder 改动）则跳过。
if command -v nm >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  _SYMS=$(mktemp); _HAY=$(mktemp); _SOS=$(mktemp)
  git status --porcelain --ignore-submodules=dirty 2>/dev/null | cut -c4- | grep -E '\.cc$' 2>/dev/null | while read -r _f; do
    [ -f "${_f}" ] || continue
    grep -hoE '[A-Za-z_][A-Za-z0-9_]*NodeRegister[[:space:]]+g_[A-Za-z0-9_]+' "${_f}" 2>/dev/null \
      | grep -oE 'g_[A-Za-z0-9_]+'
  done | sort -u > "${_SYMS}"
  if [ -s "${_SYMS}" ]; then
    find "${PKG_DIR}/tools" "${PKG_DIR}/runtime" -name '*.so' 2>/dev/null > "${_SOS}"
    while read -r _so; do nm -D "${_so}" 2>/dev/null; done < "${_SOS}" > "${_HAY}"
    _missing=""
    while read -r _s; do
      [ -z "${_s}" ] && continue
      grep -qF "${_s}" "${_HAY}" && continue           # 命中 .dynsym → 已链入
      _hit=0                                            # nm -D 未命中 → strings 兜底（罕见边角）
      while read -r _so; do strings -a "${_so}" 2>/dev/null | grep -qF "${_s}" && { _hit=1; break; }; done < "${_SOS}"
      [ "${_hit}" -eq 1 ] || _missing="${_missing} ${_s}"
    done < "${_SYMS}"
    if [ -n "${_missing}" ]; then
      echo "=================================================="
      echo "[REG-ASSERT] error: 注册符号未进链接产物——假编译成功已拦截"
      echo "[REG-ASSERT] 缺失注册全局:${_missing}"
      echo "[REG-ASSERT] 改动的 parser 里有这些 g_* 静态注册对象，.o 已编译但最终 .so 中查无此符号。"
      echo "[REG-ASSERT] 典型成因：静态库 dead-strip（无人引用被整体丢弃）或增量链接陈旧。"
      echo "[REG-ASSERT] build.sh exit 0 / 交叉库齐备 / 产物可解压，都不代表算子已链入——这正是「假编译成功」。"
      echo "[REG-ASSERT] 处置：① 新增源文件先 touch 对应 CMakeLists.txt 再 --full 重建（GLOB 需重配）；"
      echo "[REG-ASSERT]       ② 仍缺则为注册对象加强制引用 / 以 --whole-archive 链接其静态库；"
      echo "[REG-ASSERT]       ③ 修复前严禁进入 workflow Host stage：验证必失败，且会被误读为算子缺陷。"
      rm -f "${_SYMS}" "${_HAY}" "${_SOS}"
      exit 6
    fi
    echo "[REG-ASSERT] OK：注册全局已在链接产物 .dynsym 中验证存在:$(tr '\n' ' ' < "${_SYMS}")"
  else
    echo "[REG-ASSERT] 改动中无 parser 注册全局（纯复用/kernel/coder 改动）——跳过符号断言"
  fi
  rm -f "${_SYMS}" "${_HAY}" "${_SOS}"
else
  echo "[REG-ASSERT] 跳过（无 nm 或非 git 仓库）：无法核验注册符号是否进链接产物"
fi

echo "=================================================="
echo "BUILD OK（增量=$((1-FULL))）。交叉库齐备，产物已解压。"
echo "hs-verify-op-host 请使用解压包（不是 build/）："
echo "export MSLITE_PKG=${PWD}/${PKG_DIR}"
echo "==> 下一步: 返回 hs-workflow-op-development，由 workflow 调用 hs-verify-op-host；汇报时保留上面的 MSLITE_PKG 行。"
