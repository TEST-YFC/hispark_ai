---
name: hs-deploy-flash
description: Use when the user asks to "flash firmware", "burn firmware", "deploy to device", "烧录固件", "烧录", "部署到板子", "烧到板子", "flash to board", "burn to WS63", "burn to Hi3863", "flash device", "下载固件", "刷机", or after hs-verify-op passes and the user wants to deploy to hardware. Covers automatic firmware flashing to HiSilicon WS63/Hi3863 RISC-V MCU boards via CH340G/Burntool.
---

# 自动烧录固件到板端

本 skill 是交付管线的最后一环：`hs-dev-op-implement` 编译完成 + `hs-verify-op` 精度验证全绿后，
把固件烧录到 WS63/Hi3863 开发板上运行。

```
hs-dev-op-implement → hs-verify-op → hs-deploy-flash
    编译(MSLITE_PKG)    精度验证      烧录到板端
```

`hs-dev-op-implement` step6 产出 `MSLITE_PKG` 后即可进入本 skill。固件文件 (`.fwpkg`) 由用户提供路径。

## 用户能看到什么

1. **todo 进度**：每次阶段性汇报用固定 Markdown todo。
2. **门控产物**：每个 step 完成前必须在对话正文给出证据。

```markdown
状态: step<n> 进行中
待办:
- [x] step0 检查编译产物
- [ ] step1 确认 flash_server + 串口 (进行中)
- [ ] step2 确认固件文件
- [ ] step3 烧录+验证
```

某 step 标 `[x]` 的前提是其门控产物已出现在对话正文。

## 支持的目标设备

| 芯片 | 开发板 | 烧录工具 | 控制芯片 | 状态 |
|------|--------|---------|---------|------|
| **WS63 / Hi3863** | 小熊派 / 标准板 | BurnTool_H3863 | CH340G (DTR/RTS) | ✅ 全自动 |

---

## 总流程（强制顺序）

| Step | 做什么 | 门控产物 |
|------|--------|---------|
| **step0** | 检查本项目编译产物 | `PREREQ_GATE=PASS`（`check_prerequisites.sh`） |
| **step1** | 确认 flash_server + 检测串口 | health=ok + 串口列表；未就绪时**停下等用户** |
| **step2** | 确认固件文件 | 用户提供固件路径，文件存在性已校验 |
| **step3** | 烧录 + 串口验证 | `FLASH_VERDICT=PASS` + 串口有有效输出 |

---

## step0 检查本项目编译产物

```bash
bash <skill>/scripts/check_prerequisites.sh
```

检查两项：

| 检查项 | PASS 条件 | FAIL 时 |
|--------|----------|---------|
| `MSLITE_PKG` | 已设置 + `converter_lite` 可执行 | **停下**，提示先跑 `hs-dev-op-implement` step6 |
| hs-verify-op | 项目下有 `verify_summary.txt` 且 `0 FAIL` | 仅告警：`NONE`/`FAIL` 时提示用户确认风险 |

**门控**：`PREREQ_GATE=PASS` → step0 标 `[x]`；`FAIL` → **停下**。

---

## step1 确认 flash_server 就绪 + 检测设备

### 1a. 确认 flash_server 运行

flash_server 运行在 Windows 宿主机上，WSL 通过 `discover_host.sh` 自动探测可达地址（`localhost` → `$(hostname).local` → `$(hostname)` fallback）。

```bash
# host 由 discover_host.sh 自动探测，无需手动设置
curl -s --max-time 5 http://$(bash <skill>/scripts/discover_host.sh --direct):8500/health
```

关键字段：

| 字段 | 含义 | 处置 |
|------|------|------|
| `status: "ok"` | 服务就绪 | 继续 |
| `burntool_h3863_found: true` | Burntool 已自动发现 | 无需配置 |
| `burntool_h3863_found: false` | Burntool 未找到 | 提示 `set FBB_BURNTOOL=...` 后重启 flash_server |
| 连接失败 | flash_server 未启动 | **停下等用户** |

**未就绪时停下**：
```
flash_server 未响应 → 请在 Windows 终端启动 flash_server.py 后告诉我。
Burntool 未找到   → set FBB_BURNTOOL=D:\path\to\Burntool.exe 后重启 flash_server。
```

### 1b. 自动检测设备

```bash
bash <skill>/scripts/detect_device.sh
```

列出所有 CH340 串口。然后自动探测控制口/烧录口：

```bash
bash <skill>/scripts/probe_ports.sh COM10 COM11
```

探测原理（两阶段）：
1. **Phase A — power/cycle**：对候选控制口发 DTR 脉冲，验证串口可打开且 DTR 可用
2. **Phase B — serial read**：读候选烧录口串口数据（芯片复位后打印 boot 信息），这是判别烧录口的主信号

```
探测串口角色: COM10 vs COM11
  尝试: COM10=控制口 → COM11=烧录口
  ✓ power/cycle 成功 — DTR 可达
  ✗ COM11 无串口数据 — 未确认，尝试反向
  尝试: COM11=控制口 → COM10=烧录口
  ✓ power/cycle 成功 — DTR 可达
  ✓ COM10 有串口数据 (19 行) → 确认！
探测结果: CTRL=COM11  BURN=COM10
```

探测失败时输出诊断摘要，包含每个端口的 power/cycle 状态和串口读取结果。

| CH340 数量 | 处置 |
|-----------|------|
| 2 个 | 自动探测，零输入 |
| 1 个 / 0 个 | 停下，提示检查 USB 连接 |
| 探测失败 | 才问用户一次 |

**门控**：health=ok + Burntool 已发现 + 控制口和烧录口均已确认 → step1 标 `[x]`。

---

## step2 确认固件文件

### 2a. 用户指定路径（优先）

用户直接提供固件路径时，以此为准。支持 WSL 格式（`/mnt/d/.../firmware.fwpkg`）、WSL 纯路径（`/home/...`，自动拷贝到 `/mnt/d/`）和 Windows 格式（`D:\...\firmware.fwpkg`）。

WSL 路径自动转为 Windows 格式：`/mnt/<drive>/...` → `<drive>:\...`。WSL 纯路径（不在 `/mnt/` 下）会自动拷贝到第一个可用的 Windows 挂载点（`/mnt/d/` 或 `/mnt/c/`）。

### 2b. 搜索默认路径

用户未指定时，在 `application/` 和 `src/samples/` 下搜索 `.fwpkg` 和 `.bin` 文件：

```bash
find application/ src/samples/ -maxdepth 6 \( -name "*.fwpkg" -o -name "*.bin" \) -printf "%T@ %s %p\n" 2>/dev/null | sort -rn | head -10
```

| 结果 | 处置 |
|------|------|
| 1 个 | 直接使用 |
| 多个 | 列出全部（路径 + 大小），让用户选择 |
| 0 个 | 提示用户提供固件路径 |

### 2c. 校验

确认文件存在、大小 > 0。

**门控**：路径已确认 + 文件存在 → step2 标 `[x]`。

---

## step3 烧录 + 验证

### 3a. 执行烧录

```bash
curl -s --max-time 180 -X POST http://localhost:8500/flash/burntool \
  -H "Content-Type: application/json" \
  -d '{
    "firmware": "<Windows 格式路径>",
    "port": "<CH340G 控制口>",
    "burn_port": "<烧录口>",
    "baudrate": 921600
  }'
```

### 3b. FLASH_VERDICT 判定

| status | FLASH_VERDICT | 动作 |
|--------|--------------|------|
| `success` | `PASS` | 展示 `monitor_output` 中有效输出 |
| `failure` | `FAIL` | 展示 `detail` + `logs_preview`，进入修复循环 |
| `timeout` | `TIMEOUT` | 提示检查接线，尝试重新上下电 |

### 3c. 修复循环

1. 粘贴 flash_server 返回的 `detail` + `logs_preview` 尾 15 行
2. 查 `references/troubleshooting.md` 症状表
3. 呈现根因 + 修复
4. 重试

**连续 2 次失败 → 强制停下**，呈报根因分析。

---

## 红线

1. **编译未完成不烧录。** step0 `PREREQ_GATE=FAIL` 即停。
2. **flash_server 未就绪不往下走。** step1 失败即停，等用户。
3. **不绕过 flash_server API。** 严禁直接操作串口、手动 Burntool。
4. **WSL 路径必须转 Windows 格式。** `/mnt/d/...` → `D:\...`。
5. **未经验证 (VERIFY_STATUS≠PASS) 的固件烧录前提示用户确认。**

---

## 完成判据

首行状态由 `FLASH_VERDICT` 机械决定：

- `FLASH_VERDICT=PASS`：首行 `状态: 完成`
- `FLASH_VERDICT=FAIL` 或 `TIMEOUT`：首行 **只有** `状态: 未完成`

`FLASH_VERDICT≠PASS` 时禁止任何"完成/成功/✅"措辞（含换标题、括号 hedge）。

---

## 证据闸门

说以下措辞前**必须先贴对应命令输出**：

| 措辞 | 必备证据 |
|------|---------|
| flash_server 环境问题 | `/health` 完整返回 |
| 接线/串口占用 | `/serial/list` 完整返回 |
| Burntool 配置错误 | `burntool_h3863_found` 值 + 路径校验 |
| 硬件故障 | `/power/cycle` 返回 + 两次烧录的 Burntool 错误对比 |

---

## 索引

| 文件 | 何时用 |
|------|--------|
| `SKILL.md` | 本文 |
| `scripts/check_prerequisites.sh` | step0：检查 MSLITE_PKG + 验证状态 |
| `scripts/discover_host.sh` | step1：自动发现 flash_server host（WSL/localhost fallback），结果缓存 300s |
| `scripts/detect_device.sh` | step1 独立使用（串口扫描 + 板卡识别） |
| `scripts/probe_ports.sh` | step1 两个 CH340 无法区分时，自动探测控制口/烧录口 |
| `scripts/flash.sh` | step3：封装烧录（health + 路径转换 + API + 判定）；支持 WSL 路径自动拷贝 |
| `references/troubleshooting.md` | 烧录失败时按症状查 |

## 结案检查清单

- [ ] step0 `PREREQ_GATE=PASS`
- [ ] step1 health=ok + 串口列表已展示
- [ ] step2 固件路径已确认存在（WSL + Windows 双确认）
- [ ] 烧录口与控制口已确认
- [ ] `FLASH_VERDICT=PASS`
- [ ] `monitor_output` 有至少一行有效输出
- [ ] 若 VERIFY_STATUS≠PASS：用户已确认跳过验证
