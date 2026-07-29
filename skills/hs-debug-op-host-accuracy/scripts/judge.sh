#!/bin/bash
# Thin helper for re-judging a generated case with the same Python parser/cosine
# path used by run_all_cases.py and rerunnable output/<path>/_run.sh.
#
# Usage:
#   judge.sh <case_dir> [path_key]
#     case_dir : .../output/<framework>/tc<id>
#     path_key : x86_fp32 | riscv_fp32 | riscv_int8
#                omit to judge every path directory under <case_dir>/output/
set -euo pipefail

CASE="${1:?用法: judge.sh <case_dir> [path_key]}"
PATH_KEY="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
HARNESS="$SCRIPT_DIR/run_all_cases.py"

judge_one() {
  local path_key="$1"
  local out_dir="$CASE/output/$path_key"
  if [ ! -d "$out_dir" ]; then
    echo "[judge] $path_key: 跳过 ($out_dir 不存在)"
    return 1
  fi
  python3 "$HARNESS" --judge-case "$CASE" --judge-path "$path_key" \
    --stdout-log "$out_dir/stdout.log" --stderr-log "$out_dir/stderr.log"
}

if [ -n "$PATH_KEY" ]; then
  judge_one "$PATH_KEY"
  exit $?
fi

overall=0
found=0
for out_dir in "$CASE"/output/*; do
  [ -d "$out_dir" ] || continue
  found=1
  path_key="$(basename "$out_dir")"
  if ! judge_one "$path_key"; then
    overall=1
  fi
done

if [ "$found" -eq 0 ]; then
  echo "[judge] $CASE/output 下没有可判定的 path 目录"
  exit 1
fi
exit "$overall"
