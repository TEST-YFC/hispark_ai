#!/usr/bin/env bash
# 一键同步入口（方案 §4.6 默认形态 + cursor 节点）
#
#   ./sync_auto.sh                  # 同步 cursor 之后的所有单元（每笔 quick，最后 full；只 commit）
#   ./sync_auto.sh --push           # 同上，full 门禁通过后统一推送
#   ./sync_auto.sh --no-gate        # 跳过全部门禁（quick+full），台账记 gates_skipped 留痕
#   ./sync_auto.sh --dry-run        # 只看计划（纯本地读取，不 fetch）
#   ./sync_auto.sh --init <unit>    # 首次使用：声明"已同步到该单元"（含），初始化 cursor
#
# cursor 持久化在 sync_state.json 顶层 "cursor" 字段；单元失败时停在 cursor 处，
# 修复后重跑本命令即续。可挂 cron：每日执行 ./sync_auto.sh >> report/auto.log 2>&1
set -euo pipefail
cd "$(dirname "$0")"
exec python3 sync_pr.py auto "$@"
