#!/usr/bin/env python3
# Copyright 2026 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
"""上游参考 kernel 取材器（step4「参考实现对比表」的证据来源，scan_op.sh decision1′ 自动调用）。

为什么存在：对比表要求逐源记录 onnxruntime / tensorflow-lite / tflite-micro 的算法要点，
但企业网下 raw.githubusercontent.com 被墙、本地又无克隆，模型每次都只能记 UNREACHABLE
或自己瞎 curl。本脚本按镜像链（jsDelivr → ghproxy 系 → 直连 raw）取回参考 kernel 源码，
缓存到 /tmp/ref_impl/ 并打印本地路径——模型只需 Read 这些文件取算法要点，禁止凭记忆复述。

裁决语义（与 fetch_op_spec 一致，照抄进对比表）：
  FOUND       → 已下载，Read 打印的本地路径取材。
  NOT_FOUND   → 镜像可达且文件确实不存在（探测过的路径已列出）——该源按约定俗成的
                路径放不下此算子（可能在聚合文件里），对比表记 NOT_FOUND + 已探测路径。
  UNREACHABLE → 所有镜像都取不到——对比表如实记 UNREACHABLE，禁止凭记忆补"算法要点"。

用法：
  python3 fetch_ref_impl.py --op Hardmax                  # 三个仓全查
  python3 fetch_ref_impl.py --op Select --repo tflite     # 只查 tensorflow/lite/kernels
退出码恒 0（取材失败不阻塞流程，但 UNREACHABLE 必须如实写进对比表）。
"""

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_op_spec import _gh_mirror_urls  # 复用镜像链（jsDelivr → ghproxy → raw）

CACHE_ROOT = "/tmp/ref_impl"

# onnxruntime CPU kernel 的分类目录（仓库 onnxruntime/core/providers/cpu/ 下的一级目录）
ORT_BASE = "https://raw.githubusercontent.com/microsoft/onnxruntime/main/onnxruntime/core/providers/cpu/"
ORT_CATEGORIES = ["math", "tensor", "nn", "activation", "reduction", "generator",
                  "controlflow", "sequence", "rnn", "signal", "object_detection",
                  "quantization", "ml"]
# 直接路径未命中时再查的聚合文件（一文件多算子是这三个仓的常态）
ORT_BUCKETS = ["math/element_wise_ops.cc", "activation/activations.cc", "reduction/reduction_ops.cc"]

TFL_BASE = "https://raw.githubusercontent.com/tensorflow/tensorflow/master/tensorflow/lite/kernels/"
TFL_BUCKETS = ["activations.cc", "elementwise.cc", "reduce.cc", "comparisons.cc"]

MICRO_BASE = "https://raw.githubusercontent.com/tensorflow/tflite-micro/main/tensorflow/lite/micro/kernels/"
MICRO_BUCKETS = ["activations.cc", "elementwise.cc", "reduce.cc"]

FOUND, NOT_FOUND, UNREACHABLE = "FOUND", "NOT_FOUND", "UNREACHABLE"


def snake(name):
    """驼峰算子名 → 上游仓的 snake_case 文件名习惯：HardSwish→hard_swish, SelectV2→select_v2。"""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    return s.lower()


def _http_code(url, max_time=15):
    try:
        r = subprocess.run(
            ["curl", "-sL", "-o", os.devnull, "-w", "%{http_code}",
             "--connect-timeout", "6", "--max-time", str(max_time), url],
            capture_output=True, text=True, timeout=max_time + 6)
    except (OSError, subprocess.TimeoutExpired):
        return None
    code = r.stdout.strip()
    return code if code and code != "000" else None


def _download(url, max_time=40):
    try:
        r = subprocess.run(
            ["curl", "-fsSL", "--connect-timeout", "6", "--max-time", str(max_time), url],
            capture_output=True, text=True, timeout=max_time + 6)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 and r.stdout.strip() else None


def fetch(raw_url):
    """逐镜像取一个文件。返回 (FOUND, text, 实际URL) / (NOT_FOUND, None, 定论镜像URL) /
    (UNREACHABLE, None, None)。要点：404/403 也是定论（文件不存在），不再试下一跳。"""
    for u in _gh_mirror_urls(raw_url):
        code = _http_code(u)
        if code == "200":
            text = _download(u)
            if text is not None:
                return (FOUND, text, u)
        elif code in ("404", "403"):
            return (NOT_FOUND, None, u)
        # 其余（None/5xx/被墙 301 链）→ 该镜像不可达，落到下一跳
    return (UNREACHABLE, None, None)


def _save(repo, rel_path, text):
    path = os.path.join(CACHE_ROOT, repo, rel_path.replace("/", "_"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _report_hit(repo, rel_path, text, url):
    path = _save(repo, rel_path, text)
    print("  [FOUND] %s: %s（%d 行）" % (repo, path, text.count("\n") + 1))
    print("          来源: %s" % url)
    print("          → Read 该文件取「算法要点/边界情况」进对比表（仅算法核心可选优；工程骨架仍按实现指南）")


def _fetch_cached(repo, base, rel):
    """带本地缓存的 fetch——聚合文件较大且跨算子复用，多算子会话只下载一次。"""
    path = os.path.join(CACHE_ROOT, repo, rel.replace("/", "_"))
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, encoding="utf-8", errors="replace") as f:
            return (FOUND, f.read(), "本地缓存 " + path)
    verdict, text, url = fetch(base + rel)
    if verdict == FOUND:
        _save(repo, rel, text)
    return (verdict, text, url)


def probe_repo(repo, base, candidates, buckets, op):
    """先按候选直接路径探测，未中再下载聚合文件 grep 算子名。返回是否有任何命中。"""
    print("== %s ==" % repo)
    probed, unreachable = [], False
    for rel in candidates:
        verdict, text, url = fetch(base + rel)
        if verdict == FOUND:
            _report_hit(repo, rel, text, url)
            return True
        probed.append(rel)
        unreachable |= (verdict == UNREACHABLE)
    # 聚合文件兜底：一文件多算子时直接路径必然 404
    pat = re.compile(re.escape(op), re.IGNORECASE)
    for rel in buckets:
        verdict, text, url = _fetch_cached(repo, base, rel)
        if verdict == FOUND and pat.search(text):
            print("  [FOUND] %s: 算子在聚合文件 %s 内（grep '%s' 命中）" % (repo, rel, op))
            _report_hit(repo, rel, text, url)
            return True
        unreachable |= (verdict == UNREACHABLE)
    if unreachable:
        print("  [UNREACHABLE] %s: 镜像链全部取不到 → 对比表该源如实记 UNREACHABLE，禁止凭记忆补算法要点" % repo)
    else:
        print("  [NOT_FOUND] %s: 已探测 %s 及聚合文件均无 → 对比表记 NOT_FOUND（该仓可能用别的文件组织方式）"
              % (repo, ", ".join(probed[:6]) + ("…" if len(probed) > 6 else "")))
    return False


def ort_registration_evidence(op):
    """onnxruntime kernel 注册总表（单文件，含各 opset 版本区间）——既证明算子存在，
    又给出版本边界（与 fetch_op_spec 的多 opset 审计互相印证）。缓存跨会话复用。"""
    cache = os.path.join(CACHE_ROOT, "_cpu_execution_provider.cc")
    text = None
    if os.path.exists(cache) and os.path.getsize(cache) > 0:
        with open(cache, encoding="utf-8", errors="replace") as f:
            text = f.read()
    if text is None:
        verdict, text, _url = fetch(ORT_BASE + "cpu_execution_provider.cc")
        if verdict != FOUND:
            return
        with open(cache, "w", encoding="utf-8") as f:
            f.write(text)
    lines = [ln.strip() for ln in text.splitlines()
             if re.search(r"[,\s]%s\)" % re.escape(op), ln) and "KERNEL_CLASS_NAME" in ln]
    if lines:
        print("  onnxruntime 注册总表命中（cpu_execution_provider.cc，数字为 opset 版本区间）：")
        for ln in lines[:8]:
            print("    " + ln)


def main():
    ap = argparse.ArgumentParser(description="上游参考 kernel 取材器（参考实现对比表证据来源）")
    ap.add_argument("--op", required=True, help="算子名（驼峰，如 Hardmax / HardSwish / SelectV2）")
    ap.add_argument("--repo", choices=["onnxruntime", "tflite", "tflite-micro", "all"], default="all")
    args = ap.parse_args()
    op, sk = args.op, snake(args.op)

    if args.repo in ("onnxruntime", "all"):
        cands = []
        for cat in ORT_CATEGORIES:
            cands += ["%s/%s.cc" % (cat, sk), "%s/%s.h" % (cat, sk)]
        probe_repo("onnxruntime", ORT_BASE, cands, ORT_BUCKETS, op)
        ort_registration_evidence(op)
    if args.repo in ("tflite", "all"):
        probe_repo("tensorflow/lite/kernels", TFL_BASE, ["%s.cc" % sk], TFL_BUCKETS, op)
    if args.repo in ("tflite-micro", "all"):
        probe_repo("tflite-micro", MICRO_BASE, ["%s.cc" % sk], MICRO_BUCKETS, op)
    print("\n==> 命中文件已缓存 /tmp/ref_impl/，Read 后填「参考实现对比表」；"
          "UNREACHABLE/NOT_FOUND 行如实照抄，不补脑。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
