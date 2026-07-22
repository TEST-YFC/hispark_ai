#!/bin/bash
# ===================================================================
# hs-debug-op-board-accuracy 设备检测脚本
# 用法: bash detect_device.sh [--json]
# ===================================================================

set -euo pipefail

# 自动发现 flash_server host（WSL/localhost fallback）
if [[ -z "${FLASH_HOST:-}" ]]; then
    eval "$(bash "$(dirname "$0")/discover_host.sh")"
fi
FLASH_HOST="${FLASH_HOST:-localhost}"
FLASH_PORT="${FLASH_PORT:-8500}"
JSON_MODE=false
[[ "${1:-}" == "--json" ]] && JSON_MODE=true

HEALTH=$(curl -s --max-time 5 "http://${FLASH_HOST}:${FLASH_PORT}/health" 2>&1) || {
    $JSON_MODE && echo '{"error":"flash_server unreachable"}' || echo "ERROR: flash_server 未响应"
    exit 1
}

SERIAL=$(curl -s --max-time 5 "http://${FLASH_HOST}:${FLASH_PORT}/serial/list" 2>&1) || {
    $JSON_MODE && echo '{"error":"serial list failed"}' || echo "ERROR: 无法获取串口列表"
    exit 1
}

# 通过 stdin 传入 JSON，避免 shell 字符串拼接中特殊字符炸 python
echo "$HEALTH" | python3 -c "
import json, sys
health = json.load(sys.stdin)
json.dump(health, sys.stdout)
" > /tmp/hs_flash_health.json

echo "$SERIAL" | python3 -c "
import json, sys
serial = json.load(sys.stdin)
json.dump(serial, sys.stdout)
" > /tmp/hs_flash_serial.json

python3 <<PYEOF
import json

with open('/tmp/hs_flash_health.json') as f:
    h = json.load(f)
with open('/tmp/hs_flash_serial.json') as f:
    s = json.load(f)

ch34x = {p['device'] for p in h.get('ch341_ports', [])}
ports = s.get('ports', [])

# 收集所有 CH340 串口（不管驱动描述如何）
ch340_ports = []
for p in ports:
    d = p['device']
    desc = p.get('description', '')
    hwid = p.get('hwid', '')
    if d in ch34x or 'CH34' in desc or 'CH34' in hwid:
        ch340_ports.append({'device': d, 'desc': desc})

if '$JSON_MODE' == 'true':
    print(json.dumps({
        'ch340_ports': ch340_ports,
        'ch340_count': len(ch340_ports),
        'total': len(ports),
        'burntool': h.get('burntool_h3863_found', False)
    }, ensure_ascii=False, indent=2))
else:
    bt = 'OK' if h.get('burntool_h3863_found') else 'MISS'
    print(f'Burntool: {bt}  串口: {len(ports)}')
    if not ch340_ports:
        print('CH340: 未检测到 → 请检查 USB 连接')
    elif len(ch340_ports) == 1:
        print(f'CH340: {ch340_ports[0]["device"]} ({ch340_ports[0]["desc"]})')
        print('  → 仅检测到 1 个 CH340，需要 2 个（控制口 + 烧录口）')
    else:
        print(f'CH340: {len(ch340_ports)} 个')
        for p in ch340_ports:
            print(f'  {p["device"]} — {p["desc"]}')
        print(f'  → 运行 probe_ports.sh 自动探测控制口/烧录口')
PYEOF

rm -f /tmp/hs_flash_health.json /tmp/hs_flash_serial.json
