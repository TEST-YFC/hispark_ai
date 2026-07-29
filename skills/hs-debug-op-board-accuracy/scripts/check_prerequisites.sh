#!/bin/bash
# ===================================================================
# hs-debug-op-board-accuracy 烧录前置检查脚本 (SKILL.md step0 机械闸门)
#
# 检查编译产物是否就绪：MSLITE_PKG + hs-debug-op-host-accuracy 验证状态。
#
# 用法:
#   bash check_prerequisites.sh [--json]
#
# 退出码:
#   0 = 全部通过 (ALL_PASS)
#   1 = MSLITE_PKG 缺失
#
# 输出:
#   PREREQ_GATE=PASS|FAIL
#   MSLITE_PKG=OK|MISSING
#   VERIFY_STATUS=PASS|NONE
# ===================================================================

set -euo pipefail

JSON_MODE=false
[[ "${1:-}" == "--json" ]] && JSON_MODE=true

MSLITE_STATUS="MISSING"
VERIFY_STATUS="NONE"

# ---- 检查 1: MSLITE_PKG ----
check_mslite_pkg() {
    if [[ -n "${MSLITE_PKG:-}" ]] && [[ -x "$MSLITE_PKG/tools/converter/converter/converter_lite" ]]; then
        MSLITE_STATUS="OK"
        return 0
    else
        MSLITE_STATUS="MISSING"
        return 1
    fi
}

# ---- 检查 2: hs-debug-op-host-accuracy 验证状态 ----
check_verify_status() {
    local summary
    summary=$(find . -maxdepth 4 -name "verify_summary.txt" 2>/dev/null | head -1)
    if [[ -n "$summary" ]]; then
        if grep -q "0 FAIL" "$summary" 2>/dev/null; then
            VERIFY_STATUS="PASS"
            return 0
        else
            VERIFY_STATUS="FAIL"
            return 1
        fi
    else
        VERIFY_STATUS="NONE"
        return 0  # 没有验证记录不硬拦
    fi
}

# ---- 执行 ----
RC=0
check_mslite_pkg || RC=1
check_verify_status || true

# ---- 输出 ----
if $JSON_MODE; then
    python3 -c "
import json
print(json.dumps({
    'gate': 'PASS' if $RC == 0 else 'FAIL',
    'mslite_pkg': '$MSLITE_STATUS',
    'mslite_pkg_path': '${MSLITE_PKG:-}',
    'verify_status': '$VERIFY_STATUS',
}, ensure_ascii=False, indent=2))
"
else
    GATE="PASS"
    [[ $RC -ne 0 ]] && GATE="FAIL"
    echo ""
    echo "=========================================="
    echo "  hs-debug-op-board-accuracy 前置检查"
    echo "=========================================="
    echo "  MSLITE_PKG    : $MSLITE_STATUS"
    echo "  hs-debug-op-host-accuracy  : $VERIFY_STATUS"
    echo "=========================================="
    echo "  PREREQ_GATE=$GATE"
    echo ""

    if [[ "$GATE" == "FAIL" ]]; then
        echo "  [MISS] MSLITE_PKG 未设置或 converter_lite 不可执行"
        echo "         → 先跑 hs-dev-op-implement step6 编译"
        echo ""
        echo "  PREREQ_GATE=FAIL — 修复后重跑本脚本"
    fi
fi

exit $RC
