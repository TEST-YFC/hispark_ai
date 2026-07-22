"""FBB ModelZoo Flash & Serial Server

Windows 宿主机 HTTP API 服务，用于三个环境统一烧录、串口操作和电源控制：

  +----------------------------------------------+
  |  Windows 宿主机                               |
  |                                               |
  |  python agents/tools/flash_server.py          |
  |  -> 启动在 :8500                                |
  |                                               |
  |  POST /flash         烧录固件                   |
  |  POST /flash/burntool 烧录 (BurnTool_H3863)    |
  |  POST /power/on      给设备上电                 |
  |  POST /power/off     给设备断电                 |
  |  POST /power/cycle   上下电 + 进入刷机模式      |
  |  POST /serial/read   读串口输出                 |
  |  GET  /serial/list   列举可用串口                |
  |  GET  /health        健康检查                    |
  +----------------------------------------------+

三种环境调用方式：
  Windows:  curl http://localhost:8500/flash ...
  WSL:      curl http://localhost:8500/flash ...   (WSL2 localhost 映射)

依赖（Windows 宿主机安装）:
  pip install flask pyserial
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from flask import Flask, jsonify, request
except ImportError:
    print("ERROR: 需要 flask: pip install flask", file=sys.stderr)
    sys.exit(1)

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None  # 串口功能降级
    print("WARNING: 未安装 pyserial，串口功能不可用: pip install pyserial", file=sys.stderr)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

BURNTOOL_H3863_PATH = os.environ.get("FBB_BURNTOOL", r"D:\BurnTool_H3863\BurnTool.exe")
"""小熊派 Hi3863 专用 BurnTool 路径。可通过 FBB_BURNTOOL 环境变量覆盖。"""

BURNTOOL_PATHS = [
    BURNTOOL_H3863_PATH,
    r"C:\Program Files\Burntool\Burntool.exe",
    r"C:\Program Files (x86)\Burntool\Burntool.exe",
    r"C:\Burntool\Burntool.exe",
    r"C:\tools\Burntool\Burntool.exe",
]
"""可能的 Burntool 安装路径，按优先级排列。"""

PORT = int(os.environ.get("FLASH_SERVER_PORT", "8500"))
HOST = os.environ.get("FLASH_SERVER_HOST", "127.0.0.1")
"""默认仅监听本地回环地址。
WSL2 通过 localhost 映射即可访问 Windows 宿主机的 127.0.0.1，无需 0.0.0.0。
如需从其他设备访问（安全风险：烧录/串口/电源控制均为高危操作），
请设置环境变量 FLASH_SERVER_HOST=0.0.0.0。"""

H3863_CHIP_TYPE_ID = "7"
"""Hi3863 在 BurnTool 配置中的芯片类型 ID (DW31 = 7)。"""

# ---------------------------------------------------------------------------
# TCUS-1SO (CH341) 电源控制
# ---------------------------------------------------------------------------
#
# TCUS-1SO 信号控制模块通过 CH341 芯片 (COM5) 的 DTR/RTS 控制电源和刷机模式：
#
#   DTR (Pin 3)  -> Power MOSFET -> 控制板子电源
#     HIGH / True  -> Power OFF (MOSFET 关断)
#     LOW  / False -> Power ON  (MOSFET 导通)
#
#   RTS (Pin 7)  -> Boot mode -> 控制启动模式
#     LOW  / False -> Download/Flash mode (进入刷机模式)
#     HIGH / True  -> Normal boot mode (正常启动)
#
#  上电刷机时序：
#    1. DTR=HIGH (断电)
#    2. RTS=LOW  (设置为刷机模式)
#    3. DTR=LOW  (上电，进入刷机模式)
#    -> 烧录固件
#    4. DTR=HIGH (断电)
#    5. RTS=HIGH (设为正常启动模式)
#    6. DTR=LOW  (上电，正常运行)
#
#  直连 CH340 (COM6) 时无电源控制能力，需手动按复位键。
# ---------------------------------------------------------------------------


class PowerController:
    """通过 CH341 串口 DTR/RTS 控制 TCUS-1SO 电源和刷机模式。"""

    def __init__(self, port: str = "COM5", baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self._ser: serial.Serial | None = None

    def open(self) -> None:
        """打开串口连接。"""
        if serial is None:
            raise RuntimeError("pyserial 未安装，无法控制电源")
        if self._ser and self._ser.is_open:
            return
        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
        )
        # 打开串口后立即设置初始状态（先确保默认状态）
        time.sleep(0.1)

    def close(self) -> None:
        """关闭串口连接。"""
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except Exception:
                pass
        self._ser = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def set_power(self, on: bool) -> dict:
        """控制电源。

        Args:
            on: True=上电, False=断电
                DTR=HIGH -> Power OFF
                DTR=LOW  -> Power ON
        """
        if self._ser is None:
            self.open()
        assert self._ser is not None

        # DTR=True -> RTS=False -> set DTR
        dtr_state = not on  # DTR=HIGH(Power OFF) when not on; DTR=LOW(Power ON) when on
        self._ser.dtr = dtr_state
        time.sleep(0.2)

        return {
            "action": "power_on" if on else "power_off",
            "port": self.port,
            "dtr": dtr_state,
            "rts": self._ser.rts,
        }

    def set_boot_mode(self, download_mode: bool) -> dict:
        """设置启动模式。

        Args:
            download_mode: True=刷机/下载模式, False=正常启动
                pyserial rts=True -> RTS pin LOW  -> Download/Flash mode
                pyserial rts=False -> RTS pin HIGH -> Normal boot
        """
        if self._ser is None:
            self.open()
        assert self._ser is not None

        # pyserial: rts=True 输出低电平 (asserted)
        #           rts=False 输出高电平 (de-asserted)
        # RTS 低电平 -> GPIO0=低 -> 下载模式
        # RTS 高电平 -> GPIO0=高 -> 正常启动
        self._ser.rts = download_mode  # download_mode=True → rts=True → pin LOW ✓
        time.sleep(0.2)

        return {
            "action": "set_download_mode" if download_mode else "set_normal_boot",
            "port": self.port,
            "dtr": self._ser.dtr,
            "rts": self._ser.rts,
        }

    def power_cycle_into_flash(self) -> list[dict]:
        """上下电一次，并使板子进入刷机模式：

        时序: DTR=HIGH(断电) -> RTS=LOW(刷机模式) -> DTR=LOW(上电)

        Returns:
            list of step dicts
        """
        steps = []

        # 1. 断电
        self.set_power(on=False)
        steps.append({"step": 1, "action": "power_off", "dtr": self._ser.dtr if self._ser else None})
        time.sleep(0.5)

        # 2. 设置刷机模式
        self.set_boot_mode(download_mode=True)
        steps.append({"step": 2, "action": "set_flash_mode", "rts": self._ser.rts if self._ser else None})
        time.sleep(0.3)

        # 3. 上电（进入刷机模式）
        self.set_power(on=True)
        steps.append({"step": 3, "action": "power_on_in_flash_mode", "dtr": self._ser.dtr if self._ser else None})
        time.sleep(0.5)

        return steps

    def power_cycle_into_normal(self) -> list[dict]:
        """上下电一次，使板子正常启动：

        时序: DTR=HIGH(断电) -> RTS=HIGH(正常模式) -> DTR=LOW(上电)

        Returns:
            list of step dicts
        """
        steps = []

        # 1. 断电
        self.set_power(on=False)
        steps.append({"step": 1, "action": "power_off"})
        time.sleep(0.5)

        # 2. 设置正常启动模式
        self.set_boot_mode(download_mode=False)
        steps.append({"step": 2, "action": "set_normal_boot"})
        time.sleep(0.3)

        # 3. 上电（正常运行）
        self.set_power(on=True)
        steps.append({"step": 3, "action": "power_on_normal"})
        time.sleep(1.0)

        return steps


# ---------------------------------------------------------------------------
# Burntool 自动化
# ---------------------------------------------------------------------------

_BURNTOOL_DIR = Path(BURNTOOL_H3863_PATH).parent
BURNTOOL_CONFIG = _BURNTOOL_DIR / "Config.ini"
BURNTOOL_CHIP_CONFIG = _BURNTOOL_DIR / "configure" / "config_chip_type.ini"
BURNTOOL_SETTING_CONFIG = _BURNTOOL_DIR / "configure" / "config_setting.ini"


def _write_burntool_config(port: str, baudrate: int, chip_id: str = H3863_CHIP_TYPE_ID) -> None:
    """写入 BurnTool_H3863 配置文件，准备自动烧录。

    Args:
        port: COM 端口号 (如 COM5, COM6)
        baudrate: 波特率
        chip_id: 芯片类型 ID (DW31=7)
    """
    # 解析 COM 端口号 (COM5 -> 5)
    com_num = 0
    m = re.match(r"COM(\d+)", port.upper())
    if m:
        com_num = int(m.group(1))  # 1-indexed，与命令行 -com: 一致

    # 写入 Config.ini
    _log_path = str(_BURNTOOL_DIR / "QCOM_LOG.txt")
    ini_content = f"""[Set]
Baudrate={baudrate}
ByteSize=4
FlowCtrl=0
DTR_Enable=0
RTS_Enable=0
ComPort={com_num}
Parity=0
StopBits=0
SaveAsLog=0
Enter_One=0
HEX_One=0
ViewFile=0
ShowInHEX=0
FilePath=
LogPath={_log_path}
Enable_Save_Log=0
"""
    BURNTOOL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    BURNTOOL_CONFIG.write_text(ini_content, encoding="utf-8")

    # 写入 chip type 配置
    BURNTOOL_CHIP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    BURNTOOL_CHIP_CONFIG.write_text(f"[ChipType]\nCurrentChipTypeId={chip_id}\n", encoding="utf-8")

    # 写入 setting 配置
    setting_content = f"""[erase_config]
isErase=1

[setting_config]
BAUD={baudrate}

[editable_checkbox]
EDITABLE=1
"""
    BURNTOOL_SETTING_CONFIG.write_text(setting_content, encoding="utf-8")

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


COM_PORT_RE = re.compile(r"^COM\d+$", re.IGNORECASE)
"""COM 端口白名单正则，防止命令注入。"""


def _validate_com_port(port: str, field_name: str = "port") -> str:
    """验证 COM 端口格式，不合法则抛出 ValueError。

    Args:
        port: COM 端口字符串 (如 "COM5")
        field_name: 字段名，用于错误信息

    Returns:
        规范化后的端口 (如 "COM5")

    Raises:
        ValueError: 端口格式不合法
    """
    if not COM_PORT_RE.match(port):
        raise ValueError(
            f"{field_name} 格式不合法: '{port}'，必须匹配 COM\\d+ (如 COM5, COM6)"
        )
    return port.upper()


def _find_burntool() -> str | None:
    """查找 Burntool.exe，找不到返回 None。"""
    # 1. PATH 中查找
    burntool = "Burntool.exe"
    for dir_entry in os.environ.get("PATH", "").split(";"):
        candidate = Path(dir_entry) / burntool
        if candidate.is_file():
            return str(candidate)

    # 2. 常见安装路径
    for p in BURNTOOL_PATHS:
        if Path(p).is_file():
            return p

    # 3. BurnTool_H3863 专项
    if Path(BURNTOOL_H3863_PATH).is_file():
        return BURNTOOL_H3863_PATH

    return None


def _run_cmd(cmd: list[str], timeout: int = 300) -> dict:
    """运行命令并返回结构化结果。"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except FileNotFoundError:
        return {"exit_code": -1, "stdout": "", "stderr": f"命令不存在: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": f"命令超时 ({timeout}s): {' '.join(cmd)}"}


# ---------------------------------------------------------------------------
# Flask Routes
# ---------------------------------------------------------------------------

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """健康检查。"""
    burntool_path = _find_burntool()
    burntool_h3863 = Path(BURNTOOL_H3863_PATH).is_file()
    serial_available = serial is not None

    # 检测 CH341 等串口
    ch341_ports = []
    if serial is not None:
        for p in serial.tools.list_ports.comports():
            if "CH34" in p.description or "CH34" in p.hwid or "USB-SERIAL" in p.description:
                ch341_ports.append({
                    "device": p.device,
                    "description": p.description,
                })

    return jsonify({
        "status": "ok",
        "burntool_found": burntool_path is not None,
        "burntool_path": burntool_path or "",
        "burntool_h3863_found": burntool_h3863,
        "burntool_h3863_path": BURNTOOL_H3863_PATH if burntool_h3863 else "",
        "serial_available": serial_available,
        "ch341_ports": ch341_ports,
        "platform": "windows",
        "hints": {
            "windows": "curl http://localhost:8500",
            "wsl": "curl http://localhost:8500",
        },
    })


# ---------------------------------------------------------------------------
# 电源控制接口
# ---------------------------------------------------------------------------


@app.route("/power/on", methods=["POST"])
def power_on():
    """给设备上电（通过 CH341 DTR 控制 MOSFET）。

    JSON Body:
      port     (str, 可选) -- CH341 串口号, 默认 "COM5"
      baudrate (int, 可选) -- 波特率, 默认 9600

    返回:
      电源控制结果
    """
    if serial is None:
        return jsonify({"error": "pyserial 未安装，无法控制电源"}), 501

    data = request.get_json(silent=True) or {}
    port = data.get("port", "COM5")
    baudrate = data.get("baudrate", 9600)

    try:
        with PowerController(port=port, baudrate=baudrate) as ctrl:
            result = ctrl.set_power(on=True)
        return jsonify({"status": "ok", "message": "设备已上电", "detail": result})
    except Exception as exc:
        return jsonify({"error": f"上电失败: {exc}", "hint": "确认设备已连接且端口正确"}), 500


@app.route("/power/off", methods=["POST"])
def power_off():
    """给设备断电（通过 CH341 DTR 控制 MOSFET）。

    JSON Body:
      port     (str, 可选) -- CH341 串口号, 默认 "COM5"
      baudrate (int, 可选) -- 波特率, 默认 9600

    返回:
      电源控制结果
    """
    if serial is None:
        return jsonify({"error": "pyserial 未安装，无法控制电源"}), 501

    data = request.get_json(silent=True) or {}
    port = data.get("port", "COM5")
    baudrate = data.get("baudrate", 9600)

    try:
        with PowerController(port=port, baudrate=baudrate) as ctrl:
            result = ctrl.set_power(on=False)
        return jsonify({"status": "ok", "message": "设备已断电", "detail": result})
    except Exception as exc:
        return jsonify({"error": f"断电失败: {exc}"}), 500


@app.route("/power/cycle", methods=["POST"])
def power_cycle():
    """上下电一次，进入指定模式。

    JSON Body:
      port         (str, 可选) -- CH341 串口号, 默认 "COM5"
      baudrate     (int, 可选) -- 波特率, 默认 9600
      mode         (str, 可选) -- "flash" 进入刷机模式, "normal" 正常启动, 默认 "flash"

    返回:
      各步骤结果
    """
    if serial is None:
        return jsonify({"error": "pyserial 未安装，无法控制电源"}), 501

    data = request.get_json(silent=True) or {}
    port = data.get("port", "COM5")
    baudrate = data.get("baudrate", 9600)
    mode = data.get("mode", "flash")

    try:
        with PowerController(port=port, baudrate=baudrate) as ctrl:
            if mode == "flash":
                steps = ctrl.power_cycle_into_flash()
            else:
                steps = ctrl.power_cycle_into_normal()

        mode_label = "刷机模式" if mode == "flash" else "正常启动模式"
        return jsonify({
            "status": "ok",
            "message": f"上下电完成，板子已进入{mode_label}",
            "mode": mode,
            "steps": steps,
        })
    except Exception as exc:
        return jsonify({"error": f"上下电失败: {exc}"}), 500


# ---------------------------------------------------------------------------
# 烧录接口
# ---------------------------------------------------------------------------


@app.route("/flash", methods=["POST"])
def flash():
    """烧录固件到设备。

    JSON Body:
      firmware       (str, 必填) -- .fwpkg 或固件文件路径
      port           (str, 可选) -- COM 口, 默认 "COM3"
      chip           (str, 可选) -- 芯片型号, 默认 "ws63"
      baudrate       (int, 可选) -- 波特率, 默认 115200
      power_port    (str, 可选) -- CH341 电源控制端口 (如 COM5), 设置后自动上下电
      extra_args     (str, 可选) -- 附加命令行参数

    返回:
      exit_code, stdout, stderr
    """
    data = request.get_json(silent=True) or {}
    firmware = data.get("firmware", "")
    port = data.get("port", "COM3")
    chip = data.get("chip", "ws63")
    baudrate = data.get("baudrate", 115200)
    power_port = data.get("power_port", "")
    extra_args = data.get("extra_args", "")

    if not firmware:
        return jsonify({"error": "缺少必填参数: firmware"}), 400

    # 验证固件文件存在
    firmware_path = Path(firmware)
    if not firmware_path.is_file():
        return jsonify({"error": f"固件文件不存在: {firmware}"}), 400

    # -- 自动上下电（进入刷机模式）--
    power_steps = []
    if power_port and serial is not None:
        try:
            with PowerController(port=power_port, baudrate=9600) as ctrl:
                power_steps = ctrl.power_cycle_into_flash()
            app.logger.info(f"上下电成功: {power_port} -> 刷机模式")
        except Exception as exc:
            app.logger.warning(f"上下电失败（可忽略，继续烧录）: {exc}")

    # -- 使用 Burntool 烧录 --
    # 注意：Hi3863 专用烧录请使用 /flash/burntool 端点
    burntool = _find_burntool()
    if not burntool:
        return jsonify({
            "error": "找不到 Burntool.exe。请确认已安装，或设置环境变量 BURNTOOL_PATH",
            "searched": BURNTOOL_PATHS,
        }), 500

    # 构造烧录命令
    cmd = [burntool]

    burntool_lower = burntool.lower()
    if "burntool" in burntool_lower or "hispark" in burntool_lower:
        cmd.extend(["--port", str(port)])
        cmd.extend(["--baud", str(baudrate)])
        cmd.extend(["--chip", chip])
        cmd.extend(["--firmware", str(firmware_path.resolve())])
    elif "hiburn" in burntool_lower:
        cmd.extend([str(port), str(firmware_path.resolve())])
    else:
        cmd.extend(["--port", str(port)])
        cmd.extend(["--firmware", str(firmware_path.resolve())])

    if extra_args:
        cmd.extend(extra_args.split())

    app.logger.info(f"烧录命令: {' '.join(cmd)}")

    result = _run_cmd(cmd, timeout=300)
    result["chip"] = chip
    result["port"] = port
    result["firmware"] = str(firmware_path.resolve())
    result["burntool"] = burntool
    result["power_steps"] = power_steps

    if result["exit_code"] == 0:
        app.logger.info(f"烧录成功: {firmware} -> {port}")
    else:
        app.logger.warning(f"烧录失败: exit={result['exit_code']}")

    return jsonify(result)


@app.route("/flash/burntool", methods=["POST"])
def flash_burntool():
    """使用 BurnTool_H3863 烧录 Hi3863 固件（专用接口）。

    直接抄 hi3863_burn.py 的核心流程：
      写入 INI → 启动 Burntool(console) → CH340G 复位进入下载模式
      → 读 stdout 监控进度 → 恢复 GPIO0 → 复位启动固件

    JSON Body:
      firmware  (str, 必填) -- .fwpkg 固件文件路径
      port      (str, 可选) -- CH340G 控制口, 默认 "COM5"
      burn_port (str, 可选) -- Burntool 烧录口, 默认同 port
      baudrate  (int, 可选) -- 波特率, 默认 921600

    返回:
      烧录结果
    """
    data = request.get_json(silent=True) or {}
    firmware = data.get("firmware", "")
    port = data.get("port", "COM5")          # CH340G 控制口
    burn_port = data.get("burn_port", "")    # Burntool 烧录口
    baudrate = data.get("baudrate", 921600)
    invert = data.get("invert", False)

    if not firmware:
        return jsonify({"error": "缺少必填参数: firmware"}), 400

    firmware_path = Path(firmware)
    if not firmware_path.is_file():
        return jsonify({"error": f"固件文件不存在: {firmware}"}), 400
    if not Path(BURNTOOL_H3863_PATH).is_file():
        return jsonify({"error": f"BurnTool_H3863 不存在: {BURNTOOL_H3863_PATH}"}), 500

    # 白名单校验 COM 端口，防止命令注入
    try:
        port = _validate_com_port(port, "port")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if burn_port:
        try:
            burn_port = _validate_com_port(burn_port, "burn_port")
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    effective_burn_port = burn_port or port
    BURN_TIMEOUT = 120
    lines_log: list[str] = []

    def log_line(msg: str):
        lines_log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    # --- 1. 写入 INI 配置 ---
    _write_burntool_config(port=effective_burn_port, baudrate=baudrate)
    log_line(f"配置: {effective_burn_port} @ {baudrate}")

    # --- 2. 启动 Burntool (console) ---
    com_num = effective_burn_port.upper().replace("COM", "")
    # 使用 shell=False 避免 cmd.exe 解析 & | > 等 shell 元字符
    burntool_args = [
        BURNTOOL_H3863_PATH,
        f"-com:{com_num}",
        f"-bin:{firmware_path.resolve()}",
        f"-signalbaud:{baudrate}",
        "-console",
    ]
    log_line(f"启动: {' '.join(burntool_args)}")
    proc = subprocess.Popen(
        burntool_args, shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=str(BURNTOOL_CONFIG.parent),
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )
    time.sleep(2)

    # --- 3. CH340G 进入下载模式 (仿 hi3863_burn.enter_download_mode) ---
    ASSERT = False if invert else True
    DEASSERT = True if invert else False
    ch = None
    if serial is not None:
        try:
            ch = serial.Serial(port, 115200, timeout=0.1, rtscts=False, dsrdtr=False)
            time.sleep(0.1)
            ch.rts = ASSERT        # GPIO0=低 -> 下载模式
            time.sleep(0.2)
            ch.dtr = ASSERT        # 复位
            time.sleep(0.4)
            ch.dtr = DEASSERT      # 释放复位 -> 芯片在下载模式启动
            log_line(f"CH340G({port}) 复位进入下载模式")
        except Exception as exc:
            log_line(f"CH340G 控制失败: {exc}")

    # --- 4. 读 Burntool stdout 直到完成 ---
    start_ts = time.time()
    success = False
    while proc.poll() is None and time.time() - start_ts < BURN_TIMEOUT:
        try:
            line = proc.stdout.readline()
            if line:
                text = line.decode("utf-8", errors="replace").rstrip()
                if text and "QCoreApplication" not in text.lower():
                    lines_log.append(text)
                    if "burn successfully" in text.lower() or "成功" in text:
                        success = True
            else:
                time.sleep(0.02)
        except Exception:
            break
    # 读残余
    try:
        for l in (proc.stdout.read() or b"").decode("utf-8", errors="replace").split("\n"):
            l = l.strip()
            if l and "QCoreApplication" not in l.lower():
                lines_log.append(l)
                if "burn successfully" in l.lower() or "成功" in l:
                    success = True
    except Exception:
        pass
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    elapsed = time.time() - start_ts

    # --- 5. 恢复 GPIO0 并复位启动固件 (仿 hi3863_burn.restore_gpio0) ---
    DEASSERT_GPIO = True if invert else False
    if ch and ch.is_open:
        try:
            ch.rts = DEASSERT_GPIO   # GPIO0=高
            ch.close()
            log_line("GPIO0 已恢复")
        except Exception:
            pass
    elif serial is not None:
        try:
            s = serial.Serial(port, 115200, timeout=0.1, rtscts=False, dsrdtr=False)
            s.rts = False
            s.dtr = False
            s.close()
        except Exception:
            pass
    # 复位启动固件
    if serial is not None:
        try:
            s = serial.Serial(port, 115200, timeout=0.1, rtscts=False, dsrdtr=False)
            s.dtr = True
            time.sleep(0.2)
            s.dtr = False
            s.close()
            log_line("芯片已复位, 启动固件")
        except Exception:
            pass

    rc = proc.poll() or proc.returncode
    logs_text = "\n".join(lines_log)
    status = "success" if (success or rc == 0) else \
             ("timeout" if elapsed >= BURN_TIMEOUT else "failure")
    detail = {"success": "烧录完成成功", "failure": f"烧录完成失败 (返回码 {rc})",
              "timeout": f"烧录超时 ({BURN_TIMEOUT}s)"}.get(status, status)

    result = {
        "status": status,
        "detail": detail,
        "port": port,
        "burn_port": effective_burn_port,
        "firmware": str(firmware_path.resolve()),
        "burntool": str(BURNTOOL_H3863_PATH),
        "logs_preview": logs_text[:3000],
        "elapsed_s": round(elapsed, 1),
    }

    # -- 步骤 6: 监测串口输出（仿 batch_burn_and_verify.read_serial_monitor） --
    monitor_text = ""
    if status == "success" and serial is not None:
        try:
            time.sleep(2)
            mon = serial.Serial(effective_burn_port, 115200, timeout=0.5)
            mon_start = time.time()
            while time.time() - mon_start < 15:
                data = mon.read(2048)
                if data:
                    monitor_text += data.decode("utf-8", errors="replace")
                else:
                    time.sleep(0.1)
            mon.close()
        except Exception as exc:
            monitor_text = f"[串口监测错误] {exc}"
        # 解析推理结果
        pred = None
        m = re.search(r'argmax[=:]?\s*(\d+)', monitor_text, re.IGNORECASE)
        if m:
            pred = int(m.group(1))
        result["monitor_output"] = monitor_text[:2000]
        result["board_prediction"] = pred

    return jsonify(result)


# ---------------------------------------------------------------------------
# 串口接口
# ---------------------------------------------------------------------------


@app.route("/serial/list", methods=["GET"])
def serial_list():
    """列出系统可用串口。"""
    if serial is None:
        return jsonify({
            "error": "pyserial 未安装，无法列举串口",
            "install": "pip install pyserial",
        }), 501

    ports = []
    for p in serial.tools.list_ports.comports():
        ports.append({
            "device": p.device,
            "description": p.description,
            "hwid": p.hwid if hasattr(p, "hwid") else "",
        })

    return jsonify({"ports": ports, "count": len(ports)})


@app.route("/serial/read", methods=["POST"])
def serial_read():
    """从串口读取数据。

    JSON Body:
      port     (str, 必填) -- COM 口, 如 "COM3"
      baudrate (int, 可选) -- 波特率, 默认 115200
      timeout  (int, 可选) -- 读取超时秒数, 默认 5
      max_lines (int, 可选) -- 最大读取行数, 默认 50

    返回:
      data       -- 读取到的文本
      port       -- 串口号
      lines_read -- 实际读取行数
    """
    if serial is None:
        return jsonify({
            "error": "pyserial 未安装，无法读取串口",
            "install": "pip install pyserial",
        }), 501

    data = request.get_json(silent=True) or {}
    port = data.get("port", "COM3")
    baudrate = data.get("baudrate", 115200)
    timeout = data.get("timeout", 5)
    max_lines = data.get("max_lines", 50)

    try:
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            lines: list[str] = []
            for _ in range(max_lines):
                try:
                    line = ser.readline().decode(errors="replace").strip()
                    if not line:
                        break
                    lines.append(line)
                except serial.SerialTimeoutException:
                    break
                except Exception:
                    break

        text = "\n".join(lines)
        return jsonify({
            "data": text,
            "port": port,
            "lines_read": len(lines),
        })
    except serial.SerialException as exc:
        return jsonify({
            "error": f"串口打开失败: {exc}",
            "port": port,
            "hint": f"请确认设备已连接，端口 {port} 未被占用",
        }), 500


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"FBB Flash & Serial Server 启动...")
    burntool_path = _find_burntool()
    if burntool_path:
        print(f"  Burntool:     [OK] {burntool_path}")
    else:
        print(f"  Burntool:     [FAIL] 未找到，烧录功能将在运行时降级")

    burntool_h3863 = Path(BURNTOOL_H3863_PATH).is_file()
    if burntool_h3863:
        print(f"  BurnTool_H3863: [OK] {BURNTOOL_H3863_PATH}")
    else:
        print(f"  BurnTool_H3863: [FAIL] 未找到")

    if serial:
        print(f"  串口:         [OK] pyserial 就绪")
        # 检测 CH341 串口
        for p in serial.tools.list_ports.comports():
            if "CH34" in p.description or "CH34" in p.hwid:
                print(f"    -> {p.device} ({p.description}) -- 支持电源控制")
    else:
        print(f"  串口:         [FAIL] 未安装 pyserial")
    print(f"  监听:         {HOST}:{PORT}")
    if HOST == "0.0.0.0":
        print(f"  ⚠ 安全警告: 服务监听在所有网络接口 (0.0.0.0)，局域网内其他设备可访问烧录/串口/电源控制 API！")
        print(f"    如非必要，请设置 FLASH_SERVER_HOST=127.0.0.1 仅允许本地访问。")
    print(f"  接口:")
    print(f"    POST /flash         烧录固件 (通用)")
    print(f"    POST /flash/burntool 烧录固件 (BurnTool_H3863/Hi3863 专用)")
    print(f"    POST /power/on      设备上电 (CH341 DTR -> MOSFET)")
    print(f"    POST /power/off     设备断电 (CH341 DTR -> MOSFET)")
    print(f"    POST /power/cycle   上下电 + 模式切换 (刷机/正常启动)")
    print(f"    POST /serial/read   读串口")
    print(f"    GET  /serial/list   列串口")
    print(f"    GET  /health        健康检查")
    print(f"  启动方式: Windows 宿主机后台运行")
    print(f"  参考: docs/flash_server.md")
    app.run(host=HOST, port=PORT, debug=False)
