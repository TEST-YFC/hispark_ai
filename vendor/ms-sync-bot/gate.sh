#!/usr/bin/env bash
# 门禁（方案 §4.5）
#   quick 档：对变更的 C/C++ 文件跑 cpplint + cppcheck（抑制规则取自仓库 .jenkins 配置）
#   full  档：bash build.sh -e cpu 完整构建（30min+ 量级，每日/里程碑用）
# 用法: gate.sh <quick|full> <repo_b> [base]
#   quick 缺省查工作区未提交变更；给 base 提交时查 base..HEAD + 工作区
#   （用于补验已 commit 的同步，如 --no-gate 之后）
# 退出码: 0 通过; 1 失败; 2 环境缺工具（视为告警通过，需在报告中注明）
set -u
MODE="${1:-quick}"
REPO="${2:-.}"
BASE="${3:-}"

changed_c_files() {
    if [ -n "$BASE" ]; then
        git -C "$REPO" diff --name-only "$BASE" -- 2>/dev/null
        git -C "$REPO" status --porcelain | awk '{ p = substr($0, 4); gsub(/^"|"$/, "", p); print p }'
    else
        git -C "$REPO" status --porcelain | awk '{ p = substr($0, 4); gsub(/^"|"$/, "", p); print p }'
    fi | awk '/\.(cc|cpp|h|c)$/ { if (!seen[$0]++) print }'
}

# 将 .jenkins 抑制清单转成 per-file 参数（cpplint: --exclude/过滤分类; cppcheck: --suppress)
# 说明：.jenkins/check/config/filter_*.txt 的路径前缀是 CI 检出布局，按后缀匹配
lint_filters() { # $1=config文件 $2=文件名
    [ -f "$1" ] || return 0
    awk -v f="$2" '{
        line=$0; gsub(/^[ \t]+|[ \t]+$/, "", line);
        if (line ~ /^#/) next;
        gsub(/^"|"$/, "", line);
        pat=$1; rule=$2; gsub(/^"|"$/, "", pat); gsub(/^"|"$/, "", rule);
        # pat 可能是目录前缀（以 / 结尾）或文件名
        if ((pat ~ /\/$/ && index(f, substr(pat, 2)) > 0) || substr(f, length(f)-length(pat)+2) ~ substr(pat, 2)) {
            print rule
        }
    }' "$1"
}

gate_quick() {
    FILES=$(changed_c_files)
    if [ -z "$FILES" ]; then
        echo "[gate:quick] 无 C/C++ 变更，PASS"
        return 0
    fi
    echo "[gate:quick] 待检文件 $(echo "$FILES" | wc -l) 个"

    FAIL=0
    if command -v cpplint >/dev/null 2>&1; then
        CPPOPTS="--filter=-legal/copyright"
        for f in $FILES; do
            [ -f "$REPO/$f" ] || continue
            rules=$(lint_filters "$REPO/.jenkins/check/config/filter_cpplint.txt" "$f" | sed 's/^/--filter=-/' | tr '\n' ' ')
            if ! cpplint --quiet $CPPOPTS $rules "$REPO/$f" >/dev/null 2>&1; then
                echo "  ✗ cpplint: $f"
                FAIL=1
            fi
        done
        [ $FAIL -eq 0 ] && echo "  ✓ cpplint PASS"
    else
        echo "  ⚠ cpplint 未安装（告警通过）"
    fi

    if command -v cppcheck >/dev/null 2>&1; then
        CPPARGS=""
        for f in $FILES; do
            [ -f "$REPO/$f" ] || continue
            for rule in $(lint_filters "$REPO/.jenkins/check/config/filter_cppcheck.txt" "$f"); do
                CPPARGS="$CPPARGS --suppress=${rule}:*"
            done
        done
        # --suppress 放文件级会全局生效，改为逐文件运行避免误抑制
        TMP=$(mktemp)
        for f in $FILES; do
            [ -f "$REPO/$f" ] || continue
            sup=""
            for rule in $(lint_filters "$REPO/.jenkins/check/config/filter_cppcheck.txt" "$f"); do
                sup="$sup --suppress=${rule}:*"
            done
            cppcheck --quiet --inline-suppr --error-exitcode=1 \
                     --std=c++17 --language=c++ \
                     --suppress=normalCheckLevelMaxBranches \
                     $sup "$REPO/$f" >>"$TMP" 2>&1 || { echo "  ✗ cppcheck: $f"; FAIL=1; }
        done
        grep -v "^\$" "$TMP" | grep -v "^Checking" | head -20
        rm -f "$TMP"
        [ $FAIL -eq 0 ] && echo "  ✓ cppcheck PASS"
    else
        echo "  ⚠ cppcheck 未安装（告警通过）"
    fi
    return $FAIL
}

gate_full() {
    echo "[gate:full] bash build.sh -e cpu （预计 30min+）"
    (cd "$REPO" && bash build.sh -e cpu)
}

case "$MODE" in
    quick) gate_quick ;;
    full)  gate_full ;;
    *) echo "用法: gate.sh <quick|full> <repo_b>"; exit 2 ;;
esac
