#!/usr/bin/env python3
# coding: utf-8
"""hs-verify-op-board 板端精度比对脚本 (SKILL.md step3d)

从 workflow/串口工具保存的本轮 monitor 文本中提取 benchmark 打印的张量数据，
与 hs-verify-op-host 产出的 gt/output*.npy 参考输出计算余弦相似度，按双阈值机械判定。

用法:
    python board_accuracy.py --gt-dir <gt_path> --monitor <monitor_file> [--quantized]

输入:
    --gt-dir      hs-verify-op-host 产出的 gt/ 目录，内含 output.npy 或 output_0.npy, ...
    --monitor     本轮烧录后采集的完整串口 Tensor 文本文件
    --quantized   使用量化阈值 (≥ 0.99)；缺省使用非量化阈值 (≥ 0.999)

退出码:
    0 = ACCURACY_VERDICT=PASS (全部输出张量余弦达标)
    1 = ACCURACY_VERDICT=FAIL (余弦不足 或 解析失败)

设计约束（与 hs-verify-op-host 的 cosine_similarity 同语义）:
    * 两边全零 → 1.0（相符）
    * 恰好一边全零 → 0.0（真实失配 = FAIL）
    * 永不返回 NaN
"""

import argparse
import math
import re
import sys
from pathlib import Path

import numpy as np

# 硬阈值，与 SKILL.md 红线保持同步
THRESHOLD_FP32 = 0.999
THRESHOLD_INT8 = 0.99


def _read_text(path):
    """Read serial output across Windows PowerShell encoding variants."""
    raw = Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            pass
    # Serial captures can begin with a short binary/noise prefix.  Decode the
    # rest as UTF-8 with replacement when the machine-readable protocol is
    # still present; choosing a code page first would hide the ASCII markers.
    utf8_text = raw.decode("utf-8", errors="replace")
    if "[AI_MCU]" in utf8_text or "ACCURACY_VERDICT" in utf8_text:
        return utf8_text
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" not in text:
            return text
    for encoding in ("utf-16-le", "utf-16-be"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- #
# 余弦相似度（与 hs-verify-op-host/run_all_cases.py 同一实现）
# --------------------------------------------------------------------------- #

def cosine_similarity(a, b):
    """唯一的余弦函数——与 hs-verify-op-host 完全一致。

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
# 张量解析（与 hs-verify-op-host/run_all_cases.py 同一实现）
# --------------------------------------------------------------------------- #

_NUMBER_TEXT = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
_NUMBER_TOKEN = re.compile(_NUMBER_TEXT)
_MAX_PRINTED_DIM = 2**31 - 1
_FLOAT32_MAX = float(np.finfo(np.float32).max)
_OH_AI_DTYPE_TO_NUMPY = {
    30: np.dtype(np.bool_), 32: np.dtype(np.int8), 33: np.dtype(np.int16),
    34: np.dtype(np.int32), 35: np.dtype(np.int64), 37: np.dtype(np.uint8),
    38: np.dtype(np.uint16), 39: np.dtype(np.uint32), 40: np.dtype(np.uint64),
    42: np.dtype(np.float16), 43: np.dtype(np.float32), 44: np.dtype(np.float64),
}


def _parse_shape_metadata(line, prefix=r"Shape:"):
    """Return (shape, error) for a complete, non-negative Shape field."""
    suffix = r"\s*\[([^\]]*)\]"
    if prefix == r"Shape:":
        suffix += r"\s*,?\s*Data:\s*$"
    else:
        suffix += r"\s*$"
    match = re.search(r"(?:^|[,\s])" + prefix + suffix, line)
    if match is None:
        marker = "[AI_MCU] Shape:" if "AI_MCU" in prefix else "Shape:"
        error = "invalid shape metadata header" if marker in line else None
        return None, error
    raw = match.group(1).strip()
    if not raw:
        return (), None
    if re.fullmatch(r"[0-9]+(?:(?:\s*,\s*|\s+)[0-9]+)*", raw) is None:
        return None, f"invalid shape metadata: [{raw}]"
    tokens = re.findall(r"[0-9]+", raw)
    if any(len(token) > 10 for token in tokens):
        return None, "invalid shape metadata: dimension is too large"
    try:
        shape = tuple(int(token) for token in tokens)
    except (ValueError, OverflowError):
        return None, "invalid shape metadata: dimension is not an integer"
    if any(dim > _MAX_PRINTED_DIM for dim in shape):
        return None, "invalid shape metadata: dimension exceeds INT32_MAX"
    return shape, None


def _parse_elements_metadata(line):
    match = re.search(r"(?:^|[,\s])Elements:\s*([0-9]+)\s*,", line)
    if match is None:
        error = "invalid Elements metadata" if "Elements:" in line else "Elements metadata missing"
        return None, error
    token = match.group(1)
    if len(token) > 20:
        return None, "invalid Elements metadata: value is too large"
    try:
        return int(token), None
    except (ValueError, OverflowError):
        return None, "invalid Elements metadata: value is not an integer"


def _float32_array(tokens):
    values = []
    for token in tokens:
        if _NUMBER_TOKEN.fullmatch(token) is None:
            return np.array([], dtype=np.float32), f"invalid tensor data token: {token}"
        try:
            value = float(token)
        except (ValueError, OverflowError):
            return np.array([], dtype=np.float32), f"invalid tensor data token: {token}"
        if not math.isfinite(value):
            return np.array([], dtype=np.float32), "invalid tensor data: non-finite value"
        if abs(value) > _FLOAT32_MAX:
            return np.array([], dtype=np.float32), "invalid tensor data: float32 overflow"
        values.append(value)
    data = np.array(values, dtype=np.float32)
    if not np.isfinite(data).all():
        return np.array([], dtype=np.float32), "invalid tensor data: float32 overflow"
    return data, None


def _parse_benchmark_data_line(data_line):
    raw = data_line.strip()
    if not raw:
        return np.array([], dtype=np.float32), None
    parts = raw.split(",")
    if parts[-1].strip() == "":
        parts.pop()
    if not parts or any(not part.strip() for part in parts):
        return np.array([], dtype=np.float32), "invalid tensor data: empty CSV token"
    return _float32_array([part.strip() for part in parts])


def _parse_ai_mcu_data_line(line):
    match = re.fullmatch(r"\s*\[AI_MCU\]\s*Data:\s*(.*?)\s*", line)
    if match is None:
        return None, None
    payload = match.group(1)
    if re.fullmatch(rf"(?:\s*\[\s*{_NUMBER_TEXT}\s*\]\s*)*", payload) is None:
        return np.array([], dtype=np.float32), "invalid AI_MCU Data payload"
    tokens = [item.group(1).strip() for item in re.finditer(rf"\[\s*({_NUMBER_TEXT})\s*\]", payload)]
    return _float32_array(tokens)


def parse_benchmark_tensors(text):
    """从 benchmark 打印的 stdout 中提取输出张量。

    benchmark 用 PrintTensorHandle 打印时格式固定：
        <任意前缀> name:<张量名> Data:
        <逗号分隔的浮点数值>

    返回包含 data/shape/elements 的记录；shape 来自 PrintTensorHandle 元数据。
    """
    outs, lines = [], text.splitlines()
    for idx, line in enumerate(lines):
        if re.search(r"name:.*Data:\s*$", line.strip()):
            data_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
            shape, shape_error = _parse_shape_metadata(line)
            elements, elements_error = _parse_elements_metadata(line)
            data, data_error = _parse_benchmark_data_line(data_line)
            if shape is not None and math.prod(shape) == data.size:
                data = data.reshape(shape)
            outs.append({
                "data": data,
                "data_error": data_error,
                "shape": shape,
                "shape_error": shape_error,
                "elements": elements,
                "elements_error": elements_error,
            })
    return outs


def parse_benchmark_outputs(text):
    """兼容只需要平铺值的调用方。"""
    return [tensor["data"] for tensor in parse_benchmark_tensors(text)]


def parse_ai_mcu_tensors(text):
    """从 vendor 固件 serial output 中提取输出张量。

    vendor 固件用 osal_printk 打印时格式固定：
        [AI_MCU] Shape: [d1,d2,...]
        [AI_MCU] Data: [v1][v2]...[vN]

    当前协议只能无歧义表达单输出、单轮推理；多个 Data 行会明确拒绝。
    """
    lines = text.splitlines()
    indexed_protocol = any(re.fullmatch(
        r"\s*\[AI_MCU\]\s*OUTPUT:\s*index=[0-9]+\s*", line,
    ) for line in lines)
    if indexed_protocol:
        tensors = []
        current = None
        seen = set()
        for line in lines:
            output_match = re.fullmatch(
                r"\s*\[AI_MCU\]\s*OUTPUT:\s*index=([0-9]+)\s*", line,
            )
            if output_match:
                index = int(output_match.group(1))
                if current is not None and current.get("data") is None:
                    current["data_error"] = "output block has no Data line"
                    tensors.append(current)
                current = {
                    "index": index, "data": None, "data_error": None,
                    "shape": None, "shape_error": None,
                    "elements": None, "elements_error": None,
                    "dtype": None, "dtype_error": None,
                }
                if index in seen:
                    current["data_error"] = f"duplicate output index: {index}"
                seen.add(index)
                continue
            if current is None:
                continue
            dtype_match = re.fullmatch(
                r"\s*\[AI_MCU\]\s*DType:\s*([0-9]+)\s*", line,
            )
            if dtype_match:
                current["dtype"] = int(dtype_match.group(1))
                if current["dtype"] not in _OH_AI_DTYPE_TO_NUMPY:
                    current["dtype_error"] = f"unsupported DType metadata: {current['dtype']}"
                continue
            if "[AI_MCU] DType:" in line:
                current["dtype_error"] = "invalid DType metadata"
                continue
            parsed_shape, parsed_error = _parse_shape_metadata(
                line, prefix=r"\[AI_MCU\]\s*Shape:",
            )
            if parsed_shape is not None or parsed_error is not None:
                current["shape"], current["shape_error"] = parsed_shape, parsed_error
                continue
            elements_match = re.fullmatch(
                r"\s*\[AI_MCU\]\s*Elements:\s*([0-9]+)\s*", line,
            )
            if elements_match:
                current["elements"] = int(elements_match.group(1))
                continue
            if "[AI_MCU] Elements:" in line:
                current["elements_error"] = "invalid Elements metadata"
                continue
            data, data_error = _parse_ai_mcu_data_line(line)
            if data is not None:
                current["data"], current["data_error"] = data, data_error
                if current["shape"] is not None and math.prod(current["shape"]) == data.size:
                    current["data"] = data.reshape(current["shape"])
                tensors.append(current)
                current = None
        if current is not None:
            current["data_error"] = current["data_error"] or "output block has no Data line"
            tensors.append(current)
        tensors.sort(key=lambda item: item["index"])
        if [item["index"] for item in tensors] != list(range(len(tensors))):
            if tensors:
                tensors[0]["data_error"] = "output indices must be contiguous from zero"
        for tensor in tensors:
            if tensor["elements"] is None and tensor["elements_error"] is None:
                tensor["elements_error"] = "Elements metadata missing"
            if tensor["dtype"] is None and tensor["dtype_error"] is None:
                tensor["dtype_error"] = "DType metadata missing"
        return tensors

    shape = None
    shape_error = None
    tensors = []
    for line in lines:
        parsed_shape, parsed_error = _parse_shape_metadata(
            line, prefix=r"\[AI_MCU\]\s*Shape:",
        )
        if parsed_shape is not None or parsed_error is not None:
            shape, shape_error = parsed_shape, parsed_error
        data, data_error = _parse_ai_mcu_data_line(line)
        if data is not None:
            if shape is not None and math.prod(shape) == data.size:
                data = data.reshape(shape)
            tensors.append({
                "data": data,
                "data_error": data_error,
                "shape": shape,
                "shape_error": shape_error,
                "elements": None,
                "elements_error": None,
                "dtype": None,
                "dtype_error": None,
            })
    if len(tensors) > 1:
        tensors[0]["data_error"] = (
            "ambiguous AI_MCU protocol: multiple Data lines without round/output identifiers"
        )
        return tensors[:1]
    return tensors


def parse_ai_mcu_outputs(text):
    """兼容只需要数值的调用方；完整签收还要求 Shape 行。"""
    return [tensor["data"] for tensor in parse_ai_mcu_tensors(text)]


# --------------------------------------------------------------------------- #
# gt/ 加载
# --------------------------------------------------------------------------- #

def _tensor_output_name(idx, count):
    return f"output_{idx}.npy" if count > 1 else "output.npy"


def _output_file_sort_key(path: Path):
    """Sort indexed tensor files numerically, preserving the single-output name."""
    name = Path(path).name
    if name == "output.npy":
        return (0, 0, name)
    match = re.fullmatch(r"output_(\d+)\.npy", name)
    if match:
        return (1, int(match.group(1)), name)
    return (2, 0, name)


def load_gt_outputs(gt_dir):
    """加载 gt/ 下的参考输出张量，按输出索引而非字典序排列。"""
    gt_dir = Path(gt_dir)
    files = sorted(gt_dir.glob("output*.npy"), key=_output_file_sort_key)
    if not files:
        return []
    return [np.load(p) for p in files]


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(
        description="hs-verify-op-board 板端精度比对")
    ap.add_argument("--gt-dir", required=True,
                    help="hs-verify-op-host 产出的 gt/ 目录路径")
    ap.add_argument("--monitor", required=True,
                    help="本轮烧录后采集的完整串口 Tensor 文本文件")
    ap.add_argument("--quantized", action="store_true",
                    help="使用量化阈值 (≥ 0.99)；缺省使用非量化阈值 (≥ 0.999)")
    args = ap.parse_args()

    threshold = THRESHOLD_INT8 if args.quantized else THRESHOLD_FP32
    mode = "INT8" if args.quantized else "fp32"

    # 1) 读取 monitor_output
    monitor_path = Path(args.monitor)
    if not monitor_path.is_file():
        print(f"ACCURACY_VERDICT=FAIL  (monitor 文件不存在: {args.monitor})")
        sys.exit(1)
    try:
        monitor_text = _read_text(monitor_path)
    except OSError as exc:
        print(f"ACCURACY_VERDICT=FAIL  (monitor 文件读取失败: {exc})")
        sys.exit(1)

    # 2) 解析张量（优先 benchmark PrintTensorHandle 格式，fallback vendor [AI_MCU] Data: 格式）
    device_tensors = parse_benchmark_tensors(monitor_text)
    if not device_tensors:
        device_tensors = parse_ai_mcu_tensors(monitor_text)
    if not device_tensors:
        print("ACCURACY_VERDICT=FAIL  (monitor_output 中未解析到张量数据)")
        print("  → 确认固件使用了 PrintTensorHandle 打印输出张量")
        sys.exit(1)
    device_outputs = [tensor["data"] for tensor in device_tensors]

    # 3) 加载参考
    ref_outputs = load_gt_outputs(args.gt_dir)
    if not ref_outputs:
        print(f"ACCURACY_VERDICT=FAIL  (gt/ 目录无参考张量: {args.gt_dir})")
        sys.exit(1)
    if len(device_outputs) != len(ref_outputs):
        print(f"ACCURACY_VERDICT=FAIL  (张量数量不匹配: "
              f"设备={len(device_outputs)} vs 参考={len(ref_outputs)})")
        sys.exit(1)

    for i, (tensor, ref) in enumerate(zip(device_tensors, ref_outputs)):
        device = tensor["data"]
        error = (tensor["shape_error"] or tensor["elements_error"] or
                 tensor.get("dtype_error") or tensor["data_error"])
        if error is not None:
            print(
                "ACCURACY_VERDICT=FAIL  "
                f"(output[{i}] {error})"
            )
            sys.exit(1)
        if tensor["shape"] is None:
            print(
                "ACCURACY_VERDICT=FAIL  "
                f"(SHAPE_UNVERIFIED: output[{i}] 缺少机器可解析的 Shape 元数据)"
            )
            sys.exit(1)
        if tensor["elements"] is not None and tensor["elements"] != device.size:
            print(
                "ACCURACY_VERDICT=FAIL  "
                f"(output[{i}] data truncated: declared={tensor['elements']} "
                f"vs parsed={device.size})"
            )
            sys.exit(1)
        if device.size != ref.size:
            print(
                "ACCURACY_VERDICT=FAIL  "
                f"(output[{i}] element count mismatch: "
                f"device={device.size} vs reference={ref.size})"
            )
            sys.exit(1)
        if tensor["shape"] != ref.shape:
            print(
                "ACCURACY_VERDICT=FAIL  "
                f"(output[{i}] shape mismatch: "
                f"device={tensor['shape']} vs reference={ref.shape})"
            )
            sys.exit(1)
        if tensor.get("dtype") is not None and _OH_AI_DTYPE_TO_NUMPY[tensor["dtype"]] != ref.dtype:
            print(
                "ACCURACY_VERDICT=FAIL  "
                f"(output[{i}] dtype mismatch: device={_OH_AI_DTYPE_TO_NUMPY[tensor['dtype']]} "
                f"vs reference={ref.dtype})"
            )
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
