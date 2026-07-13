#!/bin/bash
# ===================================================================
# hs-deploy-flash 串口角色自动探测
#
# 当两个 CH340 串口无法自动区分控制口/烧录口时，通过两阶段自动判断：
#   Phase A — power/cycle：对端口 A 发 DTR 脉冲。若失败，说明该端口
#             不能作为控制口（串口无法打开或 DTR 不可用），直接排除。
#             若成功，继续下一步。
#   Phase B — serial read：读端口 B 的串口数据。芯片复位后会打印 boot
#             信息，这是判别烧录口的主信号。
#
# 判定逻辑:
#   power/cycle 失败 → 该端口不能是控制口，跳过此方向
#   power/cycle 成功 + 串口有数据 → 确认！ctrl=控制口, burn=烧录口
#   power/cycle 成功 + 串口无数据 → 不确定，尝试反向
#   power/cycle 提供诊断信息，串口数据是最终判别信号
#
# 用法:
#   bash probe_ports.sh <port_a> <port_b>
#   例: bash probe_ports.sh COM10 COM11
#
# 退出码:
#   0 = 检测成功，输出 CTRL=xxx BURN=xxx
#   1 = 无法确认 → 输出诊断摘要
# ===================================================================

set -euo pipefail

# 自动发现 flash_server host（WSL/localhost fallback）
if [[ -z "${FLASH_HOST:-}" ]]; then
    eval "$(bash "$(dirname "$0")/discover_host.sh")"
fi
FLASH_HOST="${FLASH_HOST:-localhost}"
FLASH_PORT="${FLASH_PORT:-8500}"

PORT_A="${1:-}"
PORT_B="${2:-}"

if [[ -z "$PORT_A" || -z "$PORT_B" ]]; then
    echo "用法: bash probe_ports.sh <port_a> <port_b>"
    exit 1
fi

echo "探测串口角色: $PORT_A vs $PORT_B"
echo "  flash_server: ${FLASH_HOST}:${FLASH_PORT}"
echo ""

# ---- 诊断记录（用于失败时汇总） ----
declare -A DIAG_PC_RESULT
declare -A DIAG_SERIAL_RESULT

# ---- Phase A: power/cycle 脉冲（返回完整响应） ----
power_cycle() {
    local port="$1"
    curl -s --max-time 5 -X POST "http://${FLASH_HOST}:${FLASH_PORT}/power/cycle" \
      -H "Content-Type: application/json" \
      -d "{\"port\":\"$port\",\"mode\":\"flash\"}" 2>&1
}

# ---- Phase B: 串口读取 ----
read_serial() {
    local port="$1"
    local timeout="${2:-4}"
    curl -s --max-time "$((timeout + 3))" -X POST "http://${FLASH_HOST}:${FLASH_PORT}/serial/read" \
      -H "Content-Type: application/json" \
      -d "{\"port\":\"$port\",\"baudrate\":115200,\"timeout\":$timeout,\"max_lines\":50}" 2>&1
}

# ---- 尝试一对端口 ----
# 返回 0 = $ctrl 确认为控制口, $burn 确认为烧录口
# 返回 1 = 未确认（power/cycle 失败 或 串口无数据）
try_pair() {
    local ctrl="$1"
    local burn="$2"

    echo "  尝试: $ctrl=控制口 → $burn=烧录口"

    # ---- Phase A: power/cycle（必要但不充分） ----
    local pc_resp
    pc_resp=$(power_cycle "$ctrl")
    local pc_status
    pc_status=$(echo "$pc_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status','error'))" 2>/dev/null || echo "parse_error")
    local pc_msg
    pc_msg=$(echo "$pc_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null || echo "")

    DIAG_PC_RESULT["$ctrl"]="$pc_status"

    if [[ "$pc_status" != "ok" ]]; then
        echo "  ✗ power/cycle 失败 ($pc_status) — $ctrl 不能作为控制口"
        [[ -n "$pc_msg" ]] && echo "    flash_server: $pc_msg"
        DIAG_SERIAL_RESULT["$burn"]="skipped(pc_fail)"
        return 1
    fi
    echo "  ✓ power/cycle 成功 — DTR 可达"
    [[ -n "$pc_msg" ]] && echo "    flash_server: $pc_msg"

    # ---- Phase B: 串口读取（主判别信号） ----
    local tmp_out="/tmp/hs_probe_${burn}.json"
    read_serial "$burn" 4 > "$tmp_out" 2>/dev/null &
    local reader_pid=$!
    sleep 0.5

    # 再次 power/cycle 触发芯片 boot 输出
    power_cycle "$ctrl" > /dev/null 2>&1
    sleep 0.5

    wait "$reader_pid" 2>/dev/null || true

    # 解析串口数据
    local ser_data
    ser_data=$(python3 -c "
import json
try:
    d = json.load(open('$tmp_out'))
    lines = d.get('lines_read', 0)
    data = d.get('data', '')
    if data and data.strip():
        print(f'DATA:{lines}:{data[:300]}')
    elif lines > 0:
        print(f'EMPTY_LINES:{lines}')
    else:
        print('EMPTY')
except Exception as e:
    print(f'ERROR:{e}')
" 2>/dev/null || echo "ERROR:python_fail")
    rm -f "$tmp_out"

    DIAG_SERIAL_RESULT["$burn"]="$ser_data"

    if echo "$ser_data" | grep -q "^DATA:"; then
        local ser_lines=$(echo "$ser_data" | cut -d: -f2)
        local ser_text=$(echo "$ser_data" | cut -d: -f3-)
        echo "  ✓ $burn 有串口数据 ($ser_lines 行) → 确认！"
        echo "    ${ser_text:0:150}"
        return 0
    else
        echo "  ✗ $burn 无串口数据 — 未确认，尝试反向"
        return 1
    fi
}

# ---- 主流程 ----
FOUND=false

# 先试 A=CTRL, B=BURN
if try_pair "$PORT_A" "$PORT_B"; then
    echo ""
    echo "探测结果: CTRL=$PORT_A  BURN=$PORT_B"
    FOUND=true
else
    echo ""
    sleep 1

    # 反过来试 B=CTRL, A=BURN
    if try_pair "$PORT_B" "$PORT_A"; then
        echo ""
        echo "探测结果: CTRL=$PORT_B  BURN=$PORT_A"
        FOUND=true
    fi
fi

# ---- 成功 ----
if $FOUND; then
    exit 0
fi

# ---- 失败：输出诊断摘要 ----
echo ""
echo "=========================================="
echo "  探测失败 — 诊断摘要"
echo "=========================================="
for port in "$PORT_A" "$PORT_B"; do
    pc="${DIAG_PC_RESULT[$port]:-未测试}"
    sr="${DIAG_SERIAL_RESULT[$port]:-未测试}"
    # 缩短串口诊断
    if echo "$sr" | grep -q "^DATA:"; then
        sr_short="有数据"
    elif echo "$sr" | grep -q "^EMPTY"; then
        sr_short="空"
    elif [[ "$sr" == "skipped" ]]; then
        sr_short="跳过(power/cycle失败)"
    else
        sr_short="$sr"
    fi
    echo "  $port  power/cycle=${pc}  serial_read=${sr_short}"
done
echo "=========================================="
echo ""
echo "可能原因:"
echo "  1. 开发板未上电（检查 USB 供电）"
echo "  2. CH340G 接线问题（DTR→Pin6, RTS→Pin22）"
echo "  3. 串口被其他程序占用"
echo "  4. 两个端口都不是控制口（检查设备管理器 COM 号）"
echo ""
echo "请手动指定控制口和烧录口后重试。"

exit 1
