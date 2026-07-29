#!/bin/bash
# ===================================================================
# hs-debug-op-board-accuracy 烧录入口脚本
#
# 用法:
#   bash flash.sh --firmware <path> [--ctrl-port COM9] [--burn-port COM4] [--baud 921600]
#
# WSL 路径 (/mnt/d/...) 自动转为 Windows 路径 (D:\...)。
# WSL 纯路径 (/home/...) 自动拷贝到 /mnt/d/ 或 /mnt/c/。
# ===================================================================

set -euo pipefail

FLASH_PORT="${FLASH_PORT:-8500}"
BAUDRATE=921600

# 自动发现 flash_server host（WSL/localhost fallback）
if [[ -z "${FLASH_HOST:-}" ]]; then
    eval "$(bash "$(dirname "$0")/discover_host.sh")"
fi
FLASH_HOST="${FLASH_HOST:-localhost}"

usage() {
    cat <<EOF
Usage: bash flash.sh --firmware <path.fwpkg> --gt-dir <path> [--ctrl-port COM9] [--burn-port COM4] [--baud 921600] [--quantized]

Arguments:
  --firmware    固件路径 (必填)
  --gt-dir      hs-debug-op-host-accuracy gt/ 目录 (必填，烧录后自动精度比对)
  --ctrl-port   CH340G 控制口 (默认 COM9)
  --burn-port   烧录口 (默认 COM4)
  --baud        波特率 (默认 921600)
  --quantized   使用量化阈值 (≥ 0.9)；缺省使用非量化阈值 (≥ 0.999999)

Exit: 0=成功 1=flash_server不可用 2=固件不存在 3=失败 4=超时 5=精度不足
EOF
}

FIRMWARE=""
CTRL_PORT=""
BURN_PORT=""
GT_DIR=""
QUANTIZED=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --firmware)  FIRMWARE="$2"; shift 2 ;;
        --ctrl-port) CTRL_PORT="$2"; shift 2 ;;
        --burn-port) BURN_PORT="$2"; shift 2 ;;
        --baud)      BAUDRATE="$2"; shift 2 ;;
        --gt-dir)    GT_DIR="$2"; shift 2 ;;
        --quantized) QUANTIZED=true; shift ;;
        -h|--help)   usage; exit 0 ;;
        *)           echo "ERROR: 未知参数: $1"; usage; exit 1 ;;
    esac
done

[[ -z "$FIRMWARE" ]] && { echo "ERROR: 缺少 --firmware"; usage; exit 1; }
[[ -z "$GT_DIR" ]] && { echo "ERROR: 缺少 --gt-dir（hs-debug-op-host-accuracy 产出的 gt/ 目录，精度比对必选）"; usage; exit 1; }
[[ -z "$CTRL_PORT" ]] && { echo "ERROR: 缺少 --ctrl-port（由 step1 自动检测提供）"; usage; exit 1; }
[[ -z "$BURN_PORT" ]] && { echo "ERROR: 缺少 --burn-port（由 step1 自动检测提供）"; usage; exit 1; }

# ---- WSL to Windows path conversion ----
to_win() {
    local p="$1"
    if [[ "$p" == /mnt/* ]]; then
        local d="${p:5:1}"
        local rest="${p:6}"
        echo "${d^^}:${rest//\//\\}"
        return 0
    else
        # Not a /mnt/ path — Windows cannot access this directly
        echo "[WSL-ONLY] $p"
        return 1
    fi
}

# ---- Ensure firmware is accessible from Windows ----
ensure_windows_path() {
    local fw="$1"

    # Already under /mnt/ — no action needed
    if [[ "$fw" == /mnt/* ]]; then
        echo "$fw"
        return 0
    fi

    # WSL-only path — auto-copy to a Windows mount point
    echo "[notice] 固件在 WSL 文件系统，需拷贝到 Windows 可访问路径..." >&2

    # Find first writable Windows mount point
    local target_drive=""
    for d in d c; do
        if [[ -d "/mnt/$d" ]] && [[ -w "/mnt/$d" ]]; then
            target_drive="$d"
            break
        fi
    done

    if [[ -z "$target_drive" ]]; then
        echo "ERROR: 没有可用的 Windows 挂载点 (/mnt/d/ 或 /mnt/c/)" >&2
        return 1
    fi

    local basename_fw
    basename_fw=$(basename "$fw")
    local dest="/mnt/${target_drive}/${basename_fw}"

    echo "[notice] 拷贝 $fw -> $dest" >&2
    cp "$fw" "$dest" || {
        echo "ERROR: 拷贝失败" >&2
        return 1
    }
    echo "[notice] 拷贝完成 ($(du -h "$dest" | cut -f1))" >&2
    echo "$dest"
}

# Execute path handling
FIRMWARE=$(ensure_windows_path "$FIRMWARE") || exit 2
WIN_FW=$(to_win "$FIRMWARE") || {
    echo "ERROR: 无法将路径转为 Windows 格式: $FIRMWARE" >&2
    echo "请将固件放到 /mnt/d/ 或 /mnt/c/ 下" >&2
    exit 2
}

echo "=========================================="
echo "  hs-debug-op-board-accuracy 烧录"
echo "=========================================="
echo "  Firmware  : $WIN_FW"
echo "  Ctrl Port : $CTRL_PORT"
echo "  Burn Port : $BURN_PORT"
echo "=========================================="

# ---- health check ----
echo ""
echo "[health] flash_server..."

HEALTH=$(curl -s --max-time 5 "http://${FLASH_HOST}:${FLASH_PORT}/health" 2>&1) || {
    echo "ERROR: flash_server 未响应 ($FLASH_HOST:$FLASH_PORT)"
    echo "请在 Windows 终端启动 flash_server.py"
    exit 1
}

echo "$HEALTH" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'  status: {d.get(\"status\",\"?\")}  burntool: {\"OK\" if d.get(\"burntool_h3863_found\") else \"MISS\"}  serial: {\"OK\" if d.get(\"serial_available\") else \"MISS\"}')
"

# ---- verify firmware ----
echo ""
echo "[verify] 固件文件..."

[[ ! -f "$FIRMWARE" ]] && { echo "ERROR: 固件不存在: $FIRMWARE"; exit 2; }
echo "  文件: $FIRMWARE ($(du -h "$FIRMWARE" | cut -f1))"

# ---- flash ----
echo ""
echo "[flash] 烧录中... (timeout 180s)"

RESPONSE=$(curl -s --max-time 180 -X POST "http://${FLASH_HOST}:${FLASH_PORT}/flash/burntool" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json, sys
print(json.dumps({
    'firmware': sys.argv[1],
    'port': sys.argv[2],
    'burn_port': sys.argv[3],
    'baudrate': int(sys.argv[4])
}))
" "$WIN_FW" "$CTRL_PORT" "$BURN_PORT" "$BAUDRATE")" 2>&1) || {
    echo "ERROR: curl 请求失败"
    exit 4
}

echo "$RESPONSE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'  status: {d.get(\"status\",\"?\")}  elapsed: {d.get(\"elapsed_s\",\"?\")}s')
print(f'  detail: {d.get(\"detail\",\"\")}')
if d.get('logs_preview'):
    print('  --- Burntool ---')
    for l in d['logs_preview'].split('\n')[-10:]:
        if l.strip(): print(f'    {l}')
if d.get('monitor_output'):
    print('  --- Serial ---')
    for l in d.get('monitor_output','').split('\n')[-15:]:
        if l.strip(): print(f'    {l.strip()}')
if d.get('board_prediction') is not None:
    print(f'  board_prediction: {d[\"board_prediction\"]}')
"

# ---- verdict (flash) ----
echo ""
STATUS=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','error'))")

FLASH_OK=false
case "$STATUS" in
    success) FLASH_OK=true; echo "  FLASH_VERDICT=PASS" ;;
    failure) echo "  FLASH_VERDICT=FAIL"; exit 3 ;;
    timeout) echo "  FLASH_VERDICT=TIMEOUT"; exit 4 ;;
    *)       echo "  FLASH_VERDICT=FAIL (unknown: $STATUS)"; exit 3 ;;
esac

# ---- step3d: accuracy comparison (always; --gt-dir is required) ----
if $FLASH_OK; then
    echo ""
    echo "[accuracy] 精度比对..."

    if [[ ! -d "$GT_DIR" ]]; then
        echo "  ACCURACY_VERDICT=FAIL  (gt/ 目录不存在: $GT_DIR)"
        echo "  → 先跑 hs-debug-op-host-accuracy 生成参考输出"
        exit 5
    fi

    # Extract monitor_output from flash response and save to temp file
    MONITOR_FILE=$(mktemp /tmp/hs_monitor.XXXXXX)
    echo "$RESPONSE" | python3 -c "
import json, sys
d = json.load(sys.stdin)
mo = d.get('monitor_output', '')
sys.stdout.write(mo if mo else '')
" > "$MONITOR_FILE"

    if [[ ! -s "$MONITOR_FILE" ]]; then
        echo "  ACCURACY_VERDICT=FAIL  (monitor_output 为空)"
        rm -f "$MONITOR_FILE"
        exit 5
    fi

    QUANT_FLAG=""
    $QUANTIZED && QUANT_FLAG="--quantized"

    # Run accuracy comparison (same cosine_similarity as hs-debug-op-host-accuracy)
    ACCURACY_SCRIPT="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)/board_accuracy.py"
    python3 "$ACCURACY_SCRIPT" --gt-dir "$GT_DIR" --monitor "$MONITOR_FILE" $QUANT_FLAG
    ACC_RC=$?
    rm -f "$MONITOR_FILE"

    if [[ $ACC_RC -ne 0 ]]; then
        echo "  ACCURACY_VERDICT=FAIL"
        exit 5
    fi
    echo "  ACCURACY_VERDICT=PASS"
fi

# ---- final ----
$FLASH_OK && exit 0
