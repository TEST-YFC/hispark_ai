#!/bin/bash
# ===================================================================
# hs-deploy-flash flash_server 自动发现
#
# 自动探测 WSL/Windows 环境下 flash_server 的可达地址。
# WSL2 中 localhost 可能不通，需要 fallback 到 $(hostname).local。
#
# 用法（由其他脚本 source）:
#   source "$(dirname "$0")/discover_host.sh"
#   # 之后 $FLASH_HOST 即为可达地址
#
# 也可独立运行:
#   bash discover_host.sh          → 输出 FLASH_HOST=<host>
#   bash discover_host.sh --direct → 直接打印 host（无 FLASH_HOST= 前缀）
#
# 缓存: /tmp/hs_flash_host（生存期 300 秒）
# ===================================================================

HOST_CACHE="/tmp/hs_flash_host"
CACHE_TTL=300

# ---- 检查缓存的 host 是否仍可达 ----
check_host() {
    local host="$1"
    curl -s --max-time 2 "http://${host}:8500/health" > /dev/null 2>&1
}

# ---- 从缓存恢复 ----
if [[ -f "$HOST_CACHE" ]]; then
    cached_host=$(cat "$HOST_CACHE" | head -1)
    cache_mtime=$(stat -c %Y "$HOST_CACHE" 2>/dev/null || echo 0)
    now=$(date +%s)
    if (( now - cache_mtime < CACHE_TTL )); then
        if check_host "$cached_host"; then
            FLASH_HOST="$cached_host"
            export FLASH_HOST
            if [[ "${1:-}" == "--direct" ]]; then
                echo "$FLASH_HOST"
            else
                echo "FLASH_HOST=$FLASH_HOST"
            fi
            return 0 2>/dev/null || exit 0
        fi
    fi
fi

# ---- 按优先级探测 ----
DISCOVERED=""

# 候选列表：优先级从高到低
CANDIDATES=("localhost" "$(hostname).local" "$(hostname)" "127.0.0.1")

for candidate in "${CANDIDATES[@]}"; do
    if check_host "$candidate"; then
        DISCOVERED="$candidate"
        break
    fi
done

# ---- 缓存结果 ----
if [[ -n "$DISCOVERED" ]]; then
    echo "$DISCOVERED" > "$HOST_CACHE"
else
    # 全部不可达，fallback 到 localhost，让后续脚本报错
    echo "localhost" > "$HOST_CACHE"
    echo "[WARN] flash_server 不可达 — 请确认 Windows 端 flash_server.py 已启动" >&2
    echo "[WARN] 已尝试: ${CANDIDATES[*]}" >&2
    DISCOVERED="localhost"
fi

FLASH_HOST="$DISCOVERED"
export FLASH_HOST

if [[ "${1:-}" == "--direct" ]]; then
    echo "$FLASH_HOST"
else
    echo "FLASH_HOST=$FLASH_HOST"
fi
