#!/usr/bin/env python3
# coding: utf-8
"""hs-debug-op-board-accuracy 板端精度比对脚本 (SKILL.md step3d)

从 flash_server 返回的 monitor_output（串口文本）中提取 benchmark 打印的张量数据，
与 hs-debug-op-host-accuracy 产出的 gt/output*.npy 参考输出计算余弦相似度，按双阈值机械判定。

用法:
    python verify_accuracy.py --gt-dir <gt_path> --monitor <monitor_file> [--quantized]

输入:
    --gt-dir      hs-debug-op-host-accuracy 产出的 gt/ 目录，内含 output.npy 或 output_0.npy, ...
    --monitor     flash_server 返回的 monitor_output 文本文件
    --quantized   使用量化阈值 (≥ 0.9)；缺省使用非量化阈值 (≥ 0.999999)

退出码:
    0 = ACCURACY_VERDICT=PASS (全部输出张量余弦达标)
    1 = ACCURACY_VERDICT=FAIL (余弦不足 或 解析失败)

设计约束（与 hs-debug-op-host-accuracy 的 cosine_similarity 同语义）:
    * 两边全零 → 1.0（相符）
    * 恰好一边全零 → 0.0（真实失配 = FAIL）
    * 永不返回 NaN
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np

# 硬阈值，与 SKILL.md 红线保持同步
THRESHOLD_FP32 = 0.999999
THRESHOLD_INT8 = 0.9


# --------------------------------------------------------------------------- #
# 余弦相似度（与 hs-debug-op-host-accuracy/run_all_cases.py 同一实现）
# --------------------------------------------------------------------------- #

def cosine_similarity(a, b):
    """唯一的余弦函数——与 hs-debug-op-host-accuracy 完全一致。

    对一切输入有定义，永不返回 NaN：
      * 两边全零 → 1.0（都没产出 = 相符）
      * 恰好一边全零 → 0.0（真实失配 = FAIL）
    """
    a = np.asarray(a).flatten().astype(np.float64)
    b = np.asarray(b).flatten().astype(np.float64)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 and nb == 0:
        return 1.0
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# --------------------------------------------------------------------------- #
# 张量解析（与 hs-debug-op-host-accuracy/run_all_cases.py 同一实现）
# --------------------------------------------------------------------------- #

def parse_benchmark_outputs(text):
    """从 benchmark 打印的 stdout 中提取输出张量。

    benchmark 用 PrintTensorHandle 打印时格式固定：
        <任意前缀> name:<张量名> Data:
        <逗号分隔的浮点数值>

    返回 list[np.ndarray]，每个元素是一个输出张量（dtype=float32）。
    """
    outs, lines = [], text.splitlines()
    for idx, line in enumerate(lines):
        if re.search(r"name:.*Data:\s*$", line.strip()):
            data_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
            vals = [float(x) for x in data_line.split(",") if x.strip()]
            if vals:
                outs.append(np.array(vals, dtype=np.float32))
    return outs


def parse_ai_mcu_outputs(text):
    """从 vendor 固件 serial output 中提取输出张量。

    vendor 固件用 osal_printk 打印时格式固定：
        [AI_MCU] Data: [v1][v2]...[vN]

    返回 list[np.ndarray]，每个元素是一个输出张量（dtype=float32）。
    只取第一次推理结果（忽略后续循环重复输出）。
    """
    lines = text.splitlines()
    for line in lines:
        if '[AI_MCU] Data: ' in line:
            vals = re.findall(r'\[(-?\d+\.\d+)\]', line)
            if vals:
                return [np.array([float(v) for v in vals], dtype=np.float32)]
    return []


# --------------------------------------------------------------------------- #
# gt/ 加载
# --------------------------------------------------------------------------- #

def _tensor_output_name(idx, count):
    return f"output_{idx}.npy" if count > 1 else "output.npy"


def load_gt_outputs(gt_dir):
    """加载 gt/ 下的参考输出张量。按文件名排序保证顺序一致。"""
    gt_dir = Path(gt_dir)
    files = sorted(gt_dir.glob("output*.npy"))
    if not files:
        return []
    return [np.load(p) for p in files]


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(
        description="hs-debug-op-board-accuracy 板端精度比对")
    ap.add_argument("--gt-dir", required=True,
                    help="hs-debug-op-host-accuracy 产出的 gt/ 目录路径")
    ap.add_argument("--monitor", required=True,
                    help="flash_server 返回的 monitor_output 文本文件")
    ap.add_argument("--quantized", action="store_true",
                    help="使用量化阈值 (≥ 0.9)；缺省使用非量化阈值 (≥ 0.999999)")
    args = ap.parse_args()

    threshold = THRESHOLD_INT8 if args.quantized else THRESHOLD_FP32
    mode = "INT8" if args.quantized else "fp32"

    # 1) 读取 monitor_output
    monitor_path = Path(args.monitor)
    if not monitor_path.is_file():
        print(f"ACCURACY_VERDICT=FAIL  (monitor 文件不存在: {args.monitor})")
        sys.exit(1)
    monitor_text = monitor_path.read_text()

    # 2) 解析张量（优先 benchmark PrintTensorHandle 格式，fallback vendor [AI_MCU] Data: 格式）
    device_outputs = parse_benchmark_outputs(monitor_text)
    if not device_outputs:
        device_outputs = parse_ai_mcu_outputs(monitor_text)
    if not device_outputs:
        print("ACCURACY_VERDICT=FAIL  (monitor_output 中未解析到张量数据)")
        print("  → 确认固件使用了 PrintTensorHandle 打印输出张量")
        sys.exit(1)

    # 3) 加载参考
    ref_outputs = load_gt_outputs(args.gt_dir)
    if not ref_outputs:
        print(f"ACCURACY_VERDICT=FAIL  (gt/ 目录无参考张量: {args.gt_dir})")
        sys.exit(1)
    if len(device_outputs) != len(ref_outputs):
        print(f"ACCURACY_VERDICT=FAIL  (张量数量不匹配: "
              f"设备={len(device_outputs)} vs 参考={len(ref_outputs)})")
        sys.exit(1)

    # 4) 逐张量计算余弦
    all_pass = True
    cos_values = []
    for i, (dev, ref) in enumerate(zip(device_outputs, ref_outputs)):
        cos = cosine_similarity(dev, ref)
        cos_values.append(cos)
        status = "PASS" if cos >= threshold else "FAIL"
        if status == "FAIL":
            all_pass = False
        name = _tensor_output_name(i, len(device_outputs))
        print(f"  {name}: cos={cos:.8f}  threshold={threshold}  {status}")

    # 5) 判定
    print(f"  mode={mode}  threshold>={threshold}")
    print(f"  min_cos={min(cos_values):.8f}")

    if all_pass:
        print("ACCURACY_VERDICT=PASS")
        sys.exit(0)
    else:
        print("ACCURACY_VERDICT=FAIL  (余弦低于阈值)")
        sys.exit(1)


if __name__ == "__main__":
    main()
