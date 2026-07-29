# 烧录故障排查

按症状查找对应的排错步骤。

## 症状速查表

| 症状 | 最可能原因 | 跳转到 |
|------|-----------|--------|
| `flash_server 不可用` | Windows 侧未启动服务 | [flash_server 未启动](#flash_server-未启动) |
| `Burntool 不存在` | 路径配置错误或未安装 | [Burntool 配置](#burntool-配置) |
| `CH340G 控制失败` | 接线错误或串口占用 | [CH340G 控制问题](#ch340g-控制问题) |
| `烧录超时 (180s)` | 设备未进入下载模式 | [烧录超时](#烧录超时) |
| `烧录成功但无串口输出` | 固件未启动或串口配置不对 | [无串口输出](#无串口输出) |
| `烧录成功但推理结果错误` | 固件与模型不匹配 | [推理结果错误](#推理结果错误) |
| `converter 报错 / 成片 FAIL` | 子模块漂移或包陈旧 | [构建环境问题](#构建环境问题) |

---

## flash_server 未启动

**症状**：
```
curl: (7) Failed to connect to localhost port 8500
```

**处置**：
1. 确认 Windows 宿主机上 flash_server.py 在运行
2. Windows 终端执行：
   ```bash
   启动 flash_server.py
   ```
3. 看到以下输出表示成功：
   ```
   FBB Flash & Serial Server 启动...
     Burntool:     [OK] D:\BurnTool_H3863\BurnTool.exe
     BurnTool_H3863: [OK] D:\BurnTool_H3863\BurnTool.exe
     串口:         [OK] pyserial 就绪
     监听:         0.0.0.0:8500
   ```

**常见失败原因**：
- `ModuleNotFoundError: No module named 'flask'` → `pip install flask pyserial`
- 端口被占用 → `netstat -ano | findstr 8500` 查看占用进程

---

## Burntool 配置

**症状**：
```
health 返回 burntool_h3863_found: false
```

**处置**：
1. 确认 `D:\BurnTool_H3863\BurnTool.exe` 存在
2. 或在环境变量中指定路径：
   ```bash
   set FBB_BURNTOOL=D:\path\to\BurnTool.exe
   ```
3. 重启 flash_server.py

**BurnTool_H3863 的标准目录结构**：
```
D:\BurnTool_H3863\
├── BurnTool.exe
├── Config.ini
├── configure\
│   ├── config_chip_type.ini
│   └── config_setting.ini
└── optLog\
```

flash_server.py 会在烧录前自动写入 `Config.ini`、`config_chip_type.ini`、`config_setting.ini`，不需要手动编辑。

---

## CH340G 控制问题

**症状**：
```
CH340G 控制失败
FLASH: 烧录失败: could not open port 'COM9'
```

**接线排查**（Hi3863）：

| CH340G 引脚 | Hi3863 引脚 | 功能 |
|------------|------------|------|
| DIR → DTR | Pin 6 (PWR/复位) | 芯片复位 |
| RTS | Pin 22 (GPIO0) | 启动模式选择 |
| GND | GND | 共地 |

**串口占用**：若有 "Access is denied" 类型的错误 → 关闭占用串口的程序（QCOM_V1.6.exe、其他终端等）。

---

## 烧录超时

**症状**：
```
status: "timeout"
detail: "烧录超时 (300s)"
```

**可能原因及处置**：

1. **设备未进入下载模式**
   - CH340G 时序不对 → 先跑 `POST /power/cycle mode=flash` 手动上下电
   - GPIO0 未拉低 → 检查 RTS 到 Pin 22 的连线

2. **烧录口不对**
   - flash_server 配置的 COM 口与设备实际连接的 COM 口不同
   - 用 `GET /serial/list` 确认串口号

3. **Burntool 未找到设备**
   - Burntool 启动了但等不到芯片响应
   - 检查芯片供电是否正常

**重试步骤**：
```bash
# 1. 上下电
curl -X POST http://localhost:8500/power/cycle -H "Content-Type: application/json" -d '{"port":"COM5","mode":"flash"}'

# 2. 重新烧录
curl -X POST http://localhost:8500/flash/burntool -H "Content-Type: application/json" -d '{"firmware":"D:\\path\\to\\firmware.fwpkg","port":"COM9","burn_port":"COM4"}'
```

---

## 无串口输出

**症状**：烧录成功（`status: success`），但 monitor_output 为空或只有乱码。

**可能原因**：
1. **波特率不对** — WS63 默认 115200，Burntool 烧录波特率 921600 是另一回事
2. **串口没复位** — 烧录完成后需要 DTR 脉冲复位芯片
3. **固件本身就是不打印的** — 最小固件可能没有串口输出

**手动监测**：
```bash
curl -X POST http://localhost:8500/serial/read -H "Content-Type: application/json" -d '{"port":"COM4","baudrate":115200,"timeout":30,"max_lines":200}'
```

---

## 推理结果错误

**症状**：烧录成功，板端有输出，但推理结果（argmax 等）与 hs-debug-op-host-accuracy 参考输出不一致。

**排查步骤**：
1. 确认烧录的是正确的 .fwpkg（检查 md5sum）
2. 确认模型输入数据与 hs-debug-op-host-accuracy 的 make_inputs() 一致
3. 烧录后重新上下电，确保是新固件在运行：
   ```bash
   curl -X POST http://localhost:8500/power/cycle -H "Content-Type: application/json" -d '{"port":"COM5","mode":"normal"}'
   ```
4. 读出完整串口输出，检查所有打印张量

---

## 构建环境问题

参见 hs-dev-op-implement `references/troubleshooting.md` 的「子模块漂移」与「构建新鲜度」节。

简要检查：
```bash
# 确认 mindspore 子模块未漂移
git -C src/mindspore log --oneline -1

# 确认 converter_lite 不旧于源码
python3 .claude/skills/hs-dev-op-implement/scripts/check_build_freshness.py \
  --code-root src/mindspore/mindspore-lite \
  --mslite-pkg "$MSLITE_PKG"
```
