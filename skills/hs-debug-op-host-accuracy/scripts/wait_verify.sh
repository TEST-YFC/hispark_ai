#!/bin/bash
# wait_verify.sh <日志文件> [max_secs=540] [pid]
#
# 阻塞等待后台 hs-debug-op-host-accuracy（run_all_cases.py）跑完——内部轮询，杜绝调用方
# "sleep N && tail" 盲等与 sleep 算术错误（sleep >110s 会被 Bash 工具默认
# 120s 超时杀掉，exit 143 是 sleep 被杀、不是验证结果）。
#
# 用法（与 nohup 启动配套；调用方把 Bash 工具 timeout 设为 (max_secs+60)*1000 毫秒）：
#   nohup python "$SKILL/scripts/run_all_cases.py" --spec scripts/op_spec.py \
#       > /tmp/op_verify.log 2>&1 & echo $! > /tmp/op_verify.pid
#   bash "$SKILL/scripts/wait_verify.sh" /tmp/op_verify.log 540 "$(cat /tmp/op_verify.pid)"
#
# 退出码：0 = 日志已出 VERDICT（贴出末尾结论，照抄汇报）
#         1 = 进程已退出但没有 VERDICT（前置检查/闸门拦截或崩溃——读贴出的日志定位）
#        10 = 到时仍在跑——再跑一次本脚本接着等（不要杀进程、不要重启验证）
# 注意：本脚本退出码 0 只表示"VERDICT 已出现"，PASS/FAIL 看日志里 VERDICT 后的
# HARNESS_EXIT=N 行（0=全 PASS，非 0=有 FAIL）。禁止自行 `grep -c FAIL` 之类计数判定
# ——VERDICT 的 "0 FAIL" 字样也会被计入，全绿会被误判成失败。
set -u
LOG="${1:?用法: wait_verify.sh <日志文件> [max_secs] [pid]}"
MAX="${2:-540}"
PID="${3:-}"
case "${MAX}" in (*[!0-9]*|"") echo "[!] max_secs 须为秒数" >&2; exit 1;; esac

waited=0
while :; do
  if grep -q "^VERDICT:" "${LOG}" 2>/dev/null; then
    echo "DONE——日志末尾（VERDICT 行照抄进汇报，不得复述/美化）："
    tail -40 "${LOG}"
    ex="$(grep -o '^HARNESS_EXIT=[0-9]*' "${LOG}" 2>/dev/null | tail -1)"
    if [ -n "${ex}" ]; then
      echo "[i] harness 退出码：${ex}（0=全 PASS，非 0=有 FAIL）——退出码只认这一行。"
    else
      echo "[i] 日志无 HARNESS_EXIT 行（旧版 harness）——以 VERDICT 行的 'N FAIL' 数为准。"
    fi
    echo "    禁止自行 'grep -c FAIL' 之类计数判定——VERDICT 的 '0 FAIL' 也含 'FAIL' 字样，全绿会被误判为失败。"
    exit 0
  fi
  if [ -n "${PID}" ] && ! kill -0 "${PID}" 2>/dev/null; then
    echo "EXITED_NO_VERDICT——进程已退出但日志无 VERDICT（前置检查/闸门拦截或崩溃），日志末尾："
    tail -40 "${LOG}"
    exit 1
  fi
  if [ "${waited}" -ge "${MAX}" ]; then
    echo "RUNNING（已等 ${waited}s，达到上限）——日志末尾："
    tail -8 "${LOG}" 2>/dev/null
    echo "[i] 再跑一次本脚本接着等；不要杀进程、不要另起验证"
    exit 10
  fi
  sleep 15
  waited=$((waited + 15))
done
