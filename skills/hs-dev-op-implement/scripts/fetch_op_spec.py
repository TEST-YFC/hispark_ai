#!/usr/bin/env python3
# Copyright 2026 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
"""算子框架存在性裁决器（hs-dev-op-implement skill 的 decision1 证据来源）。

为什么存在：某框架是否定义某算子是**确定性事实**，但凭记忆判断并不可靠——同名
算子可能在某框架根本不存在，或在不同框架命名不同。本脚本对每个框架给出
FOUND / NOT_FOUND / UNREACHABLE 的裁决，**其输出直接作为 decision1/decision4 的查证证据**：

  - 某框架 NOT_FOUND  → 不为该框架建 parser、不为该框架造 hs-debug-op-host-accuracy 用例。
  - 全部 UNREACHABLE  → 非零退出 → 停下问用户（禁止凭记忆继续）。

裁决基于真实可引的产物（ONNX Operators.md 锚点 / onnx.com.cn 页面 HTTP 码 /
TFLite builtin_ops.h 枚举），模型无法"绕过"——NOT_FOUND 不会留下任何可粘贴为
"FOUND 证据"的东西。

用法：
  python3 fetch_op_spec.py --op Select                 # 查 ONNX + TFLite
  python3 fetch_op_spec.py --op Where --framework onnx
  python3 fetch_op_spec.py --op SelectV2 --framework tflite

退出码：所请求的每个框架都有定论（FOUND 或 NOT_FOUND）→ 0；
        任一框架 UNREACHABLE → 非零（→ 走 decision1 兜底，问用户，不要猜）。

注意：裁决针对**所给的确切名字**。同一算子在不同框架名字可能不同
（如 ONNX `Conv` vs TFLite `Conv2d`），某框架 NOT_FOUND 时，若你有理由认为它在
该框架用了别的名字，用那个名字再查一次——但不得在无 FOUND 证据时断言其存在。
"""

import argparse
import html
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REFS = os.path.join(SCRIPT_DIR, "..", "references")

ONNX_RAW = "https://raw.githubusercontent.com/onnx/onnx/main/docs/Operators.md"
ONNX_PAGE = "https://onnx.com.cn/onnx/operators/onnx__{op}.html"
TFLITE_RAW = ("https://raw.githubusercontent.com/tensorflow/tensorflow/"
              "master/tensorflow/lite/builtin_ops.h")
# tf2onnx 的 @tf_op 注册表 = "TF/TFLite 名 ↔ ONNX 名"的权威映射字典（decision2 跨名候选的通用来源）
TF2ONNX_BASE = "https://raw.githubusercontent.com/onnx/tensorflow-onnx/main/tf2onnx/onnx_opset/"
TF2ONNX_FILES = ["math.py", "tensor.py", "nn.py", "controlflow.py", "logical.py",
                 "reduction.py", "generator.py", "rnn.py", "misc.py", "quantize.py", "signal.py"]

FOUND, NOT_FOUND, UNREACHABLE = "FOUND", "NOT_FOUND", "UNREACHABLE"


def _read_local(path):
    """读本地克隆文件；空文件 / 404 / HTML 错误页一律当不存在（返回 None）。"""
    try:
        if os.path.getsize(path) <= 0:
            return None
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    head = text[:200].lower()
    if "404: not found" in head or "<html" in head:
        return None
    return text


# raw.githubusercontent.com 在部分企业网被墙——GitHub raw URL 自动走镜像链重试：
# jsDelivr CDN（快；但 >2MB 文件会 301 回 raw，被墙时该跳失败、自动落下一跳）
# → ghproxy 系前缀代理（无大小限制）→ 直连 raw 兜底。
# 环境变量 OP_SPEC_GH_MIRROR 可前插自定义前缀代理（形如 https://my-proxy/，拼在 raw URL 前）。
_GH_RAW_RE = re.compile(r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$")
_GH_PROXY_PREFIXES = ["https://ghproxy.net/", "https://gh-proxy.com/", "https://ghfast.top/"]


def _gh_mirror_urls(url):
    """GitHub raw URL → 按优先级排列的镜像 URL 列表；非 raw URL 原样返回。"""
    m = _GH_RAW_RE.match(url)
    if m is None:
        return [url]
    owner, repo, branch, path = m.groups()
    custom = os.environ.get("OP_SPEC_GH_MIRROR")
    prefixes = ([custom.rstrip("/") + "/"] if custom else []) + _GH_PROXY_PREFIXES
    return (["https://cdn.jsdelivr.net/gh/%s/%s@%s/%s" % (owner, repo, branch, path)]
            + [p + url for p in prefixes] + [url])


def _curl_one(url, max_time):
    """单 URL curl；-f 使 404/5xx 失败（jsDelivr 的 404 错误页是 200 文本，不加 -f 会被当成文件内容）。"""
    try:
        r = subprocess.run(
            ["curl", "-fsSL", "--connect-timeout", "6", "--max-time", str(max_time), url],
            capture_output=True, text=True, timeout=max_time + 6)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout
    return None


_LAST_FETCH_URL = None  # 最近一次成功取数的真实 URL（可能是镜像）——证据行必须引用它而非原始 raw URL


def _curl(url, max_time=20):
    """curl 取文本（带超时）；GitHub raw URL 自动按镜像链逐跳重试；全部失败返回 None。"""
    global _LAST_FETCH_URL
    for u in _gh_mirror_urls(url):
        text = _curl_one(u, max_time)
        if text is not None:
            _LAST_FETCH_URL = u
            return text
    return None


def _curl_http_code(url, max_time=15):
    """只取 HTTP 状态码（用于页面存在性探测）；失败返回 None。"""
    try:
        r = subprocess.run(
            ["curl", "-sL", "-o", os.devnull, "-w", "%{http_code}",
             "--connect-timeout", "6", "--max-time", str(max_time), url],
            capture_output=True, text=True, timeout=max_time + 6)
    except (OSError, subprocess.TimeoutExpired):
        return None
    code = r.stdout.strip()
    return code if code and code != "000" else None


def _strip_html(text):
    return html.unescape(re.sub(r"<[^>]*>", "", text))


def _onnx_local_schema(op):
    """来源 0：本地安装的 onnx python 包（hs-debug-op-host-accuracy 环境必装）——权威且完全离线。
    返回 (FOUND, schema) / (NOT_FOUND, None) / (None, None)（包不可用，降级后续来源）。"""
    try:
        from onnx import defs
        if not defs.has(op):
            return (NOT_FOUND, None)
        return (FOUND, defs.get_schema(op))
    except ImportError:
        return (None, None)
    except Exception:
        return (None, None)


def _attr_default_str(a):
    """属性默认值 → 可读字符串；无默认返回 ""。供属性表与多版本审计共用。"""
    from onnx import AttributeProto
    d = a.default_value
    if d is None or not d.type:
        return ""
    getter = {AttributeProto.INT: lambda: d.i,
              AttributeProto.FLOAT: lambda: round(d.f, 6),
              AttributeProto.STRING: lambda: d.s.decode("utf-8", "replace"),
              AttributeProto.INTS: lambda: list(d.ints),
              AttributeProto.FLOATS: lambda: [round(x, 6) for x in d.floats]}
    return str(getter.get(d.type, lambda: "<复合类型，查规格页>")())


def _onnx_attr_table(op):
    """属性表（名/类型/必需/默认值）+ 输入输出 + 类型约束——直接从本地 onnx 包 schema 读出。
    属性审计（step4 写 ② 前的强制动作）可据此离线完成，免去 WebFetch 被墙后的反复绕路。"""
    st, s = _onnx_local_schema(op)
    if st != FOUND:
        return None
    out = ["属性表（本地 onnx 包 onnx.defs.get_schema('%s')，since opset %d——权威，属性审计直接用）："
           % (op, s.since_version)]
    if not s.attributes:
        out.append("  （无属性）")
    for name, a in sorted(s.attributes.items()):
        dv = _attr_default_str(a)
        out.append("  %s: %s %s%s" % (name, str(a.type).split(".")[-1],
                                      "必需" if a.required else "可选",
                                      " 默认=%s" % dv if dv else ""))
    fmt = lambda ps: ", ".join("%s(%s%s)" % (p.name,
                               getattr(p, "type_str", None) or getattr(p, "typeStr", "?"),
                               "" if str(p.option).endswith("Single") else ",%s" % str(p.option).split(".")[-1])
                               for p in ps)
    out.append("  输入: %s" % fmt(s.inputs))
    out.append("  输出: %s" % fmt(s.outputs))
    for tc in s.type_constraints:
        out.append("  类型约束 %s ∈ {%s}（kernel dtype 覆盖面据此定）"
                   % (tc.type_param_str, ", ".join(tc.allowed_type_strs)))
    return "\n  ".join(out)


def _onnx_doc_excerpt(op, max_lines=20):
    """规格 Doc 正文——语义真值所在（平局规则/边界行为/公式都在这）。
    必须打印进 scan 输出：否则模型会自写 onnx 内省脚本去取（实证：崩溃两次还差点猜语义）。"""
    st, s = _onnx_local_schema(op)
    if st != FOUND or not (s.doc or "").strip():
        return None
    lines = [ln.rstrip() for ln in s.doc.strip().splitlines() if ln.strip()]
    head, total = lines[:max_lines], len(lines)
    tail = ("" if total <= max_lines else
            "\n  …(共 %d 行，看全文: python3 -c \"from onnx import defs; print(defs.get_schema('%s').doc)\")"
            % (total, op))
    return ("规格 Doc 原文前 %d 行（onnx.defs.get_schema('%s').doc——平局/边界语义只认这里，禁凭记忆）：\n  %s%s"
            % (len(head), op, "\n  ".join(head), tail))


def _onnx_version_audit(op):
    """多 opset 版本审计：同名算子在不同 opset 的属性默认值/属性集可能不同，语义甚至整体改变
    （实证盲区：Hardmax axis 默认值 opset≤11 是 1 且语义为 flatten-2D 整体 hardmax，
    opset 13 起是 -1 逐轴——只看最新 schema 写 parser，旧 opset 模型会静默算错）。"""
    try:
        from onnx import defs
        hist = sorted((s for s in defs.get_all_schemas_with_history()
                       if s.name == op and not s.deprecated),
                      key=lambda s: s.since_version)
    except Exception:
        return None
    if len(hist) <= 1:
        return None
    per_ver = [(s.since_version, {n: _attr_default_str(a) for n, a in s.attributes.items()})
               for s in hist]
    out = ["opset 版本史: %s（该算子有多个 opset 版本）" % ", ".join(str(v) for v, _ in per_ver)]
    all_names = sorted({n for _, attrs in per_ver for n in attrs})
    changed = []
    for n in all_names:
        vals = [(v, attrs.get(n, "<无此属性>")) for v, attrs in per_ver]
        if len({val for _, val in vals}) > 1:
            changed.append("%s: %s" % (n, ", ".join("opset%d=%s" % (v, val) for v, val in vals)))
    if changed:
        out.append("[!] 属性默认值/属性集随 opset 变化——parser 不得只按最新默认值写死：")
        for c in changed:
            out.append("    " + c)
        out.append("    → 处置二选一：parser 按模型 opset 分支处理；或对旧 opset 显式 MS_LOG(ERROR) 拒绝。")
        out.append("    旧版语义可能整体不同（不止默认值）——逐版本核对 Doc："
                   "python3 -c \"from onnx import defs; print(defs.get_schema('%s', <opset>).doc)\"" % op)
    else:
        out.append("[i] 各版本属性默认值未变，但语义文本仍可能随版本变化（机检不到）——"
                   "模型 opset 低于 %d 时核对旧版 Doc 再下结论。" % per_ver[-1][0])
    return "\n  ".join(out)


def onnx_semantics(op):
    """ONNX 语义段：本地 onnx 包属性表 + Doc 正文 + 多 opset 版本审计（权威且离线）；
    本地包不可用时退回 Operators.md 算子小节（描述/广播约束）。"""
    parts = [p for p in (_onnx_attr_table(op), _onnx_doc_excerpt(op), _onnx_version_audit(op)) if p]
    if not parts:
        text = _read_local(os.path.join(SCRIPT_DIR, "..", "references", "onnx", "docs", "Operators.md")) \
            or _curl(ONNX_RAW)
        if text is not None:
            m = re.search(r'<a name="%s">' % re.escape(op), text)
            if m is not None:
                plain = _strip_html(text[m.start():m.start() + 2000])
                lines = [ln.strip() for ln in plain.splitlines() if ln.strip()]
                parts.append("\n  ".join(lines[:12]))
    return "\n  ".join(parts) if parts else None


def tflite_semantics(op):
    """TFLite 语义段(决定广播/形状约束——非广播版与广播版变体的关键区别常在此),取自 tfl_ops。"""
    text = _curl("https://tensorflow.google.cn/mlir/tfl_ops")
    if text is None:
        return None
    plain = _strip_html(text)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", op).lower()  # SelectV2 → select_v2
    for name in dict.fromkeys([snake, op.lower()]):
        m = re.search(r"tfl\.%s \(TFL" % re.escape(name), plain)
        if m is None:
            continue
        seg = plain[m.start():m.start() + 1500]
        nxt = re.search(r"\ntfl\.\w+ \(TFL", seg[20:])  # 截到下一个算子小节
        if nxt:
            seg = seg[:nxt.start() + 20]
        lines = [ln.strip() for ln in seg.splitlines() if ln.strip()]
        return "\n  ".join(lines[:16])
    return None


def _tf2onnx_sources(refs_dir):
    """逐文件产出 (文件名, 文本)：本地克隆优先，否则 curl 并缓存到 /tmp 供跨会话复用。"""
    import tempfile
    for name in TF2ONNX_FILES:
        text = _read_local(os.path.join(refs_dir, "tensorflow-onnx", "tf2onnx", "onnx_opset", name))
        if text is None:
            cache = os.path.join(tempfile.gettempdir(), "tf2onnx_opset_" + name)
            text = _read_local(cache)
            if text is None:
                text = _curl(TF2ONNX_BASE + name, max_time=25)
                if text:
                    try:
                        with open(cache, "w", encoding="utf-8") as f:
                            f.write(text)
                    except OSError:
                        pass
        if text:
            yield name, text


def cross_ref(op, refs_dir):
    """跨框架映射字典探测（decision2 候选来源④，对任意算子通用）。

    原理：tf2onnx 用 @tf_op("名"/["名",...]) 注册每个 TF/TFLite 算子的转换 handler，
    handler 体内 make_node("X")/node.type="X" 即它落到的 ONNX 算子名——这是一份持续
    维护的权威同义词典，覆盖全部受支持算子，无需本 skill 逐族硬编码。两个方向：
      正向：本算子是 TF/TFLite 名 → 它的 ONNX 落点（ONNX 名通常直接对得上仓内 schema/parser）。
      反向：本算子是 ONNX 名 → 哪些 TF/TFLite 算子落到它（提示同族变体）。
    输出仅是候选线索：等价性仍按 decision2 四条、以仓内 infer/kernel 与规格逐项裁决。
    退出码恒 0（探测失败不阻塞流程，但会明示"人工语义检索不可省"）。"""
    fwd, rev, reached = {}, {}, False
    for fname, text in _tf2onnx_sources(refs_dir):
        reached = True
        for block in re.split(r"(?=@tf_op\()", text):
            m = re.match(r'@tf_op\(\s*(\[[^\]]*\]|"[^"]*")', block)
            if not m:
                continue
            tf_names = re.findall(r'"([^"]+)"', m.group(1))
            onnx_names = set(re.findall(r'make_node\(\s*"([A-Za-z0-9]+)"', block)) \
                | set(re.findall(r'node\.type\s*=\s*"([A-Za-z0-9]+)"', block)) \
                | set(re.findall(r'op_type\s*=\s*"([A-Za-z0-9]+)"', block))
            if any(n.lower() == op.lower() for n in tf_names):
                for x in onnx_names:
                    fwd.setdefault(x, fname)
            if any(n.lower() == op.lower() for n in onnx_names):
                for x in tf_names:
                    rev.setdefault(x, fname)
    print("== 跨框架映射字典探测(tf2onnx @tf_op 注册表): op=%s ==" % op)
    if not reached:
        print("字典取不到（references/ 无 tensorflow-onnx 克隆且 curl 失败）"
              "→ 跨名同义候选只能靠 decision2 人工语义检索，不可省。")
        return 0
    if fwd:
        print("正向 TF/TFLite \"%s\" 的 ONNX 落点（handler 体内生成的节点，含辅助算子，需人工甄别主算子）:" % op)
        for x, f in sorted(fwd.items()):
            print("  %s  (证据: tf2onnx/onnx_opset/%s)" % (x, f))
    if rev:
        print("反向 ONNX \"%s\" 被这些 TF/TFLite 算子落到（同族/变体提示）:" % op)
        for x, f in sorted(rev.items()):
            print("  %s  (证据: tf2onnx/onnx_opset/%s)" % (x, f))
    cands = sorted(set(fwd) | set(rev))
    if cands:
        print("CROSS_REF_CANDIDATES: " + " ".join(cands))
        print("（不在 schema union 里的名字，grep tools/converter/parser/ 看它被哪个已有 parser 映射到哪个 PrimType）")
    else:
        print("（字典可达但无 %s 的映射记录——不构成否定证据，decision2 人工语义检索照做）" % op)
    return 0


def lookup_onnx(op, refs_dir):
    """ONNX 存在性：本地 onnx 包 → Operators.md 锚点 → raw 同文件 → onnx.com.cn 页面 HTTP 码。"""
    # 来源 0：本地安装的 onnx python 包（权威、完全离线、企业网不可达时仍可用）
    st, schema = _onnx_local_schema(op)
    if st == FOUND:
        return (FOUND, "本地 onnx 包 onnx.defs.get_schema('%s') 命中（since opset %d）"
                % (op, schema.since_version))
    if st == NOT_FOUND:
        return (NOT_FOUND, "本地 onnx 包 onnx.defs.has('%s') = False → ONNX 不定义此算子名" % op)
    # 来源 1/2：Operators.md（本地优先，再 curl raw）——按精确锚点 name="Op" 判定
    text = _read_local(os.path.join(refs_dir, "onnx", "docs", "Operators.md"))
    src = "本地 references/onnx/docs/Operators.md"
    if text is None:
        text = _curl(ONNX_RAW)
        src = _LAST_FETCH_URL or ONNX_RAW
    if text is not None:
        m = re.search(r'<a name="%s">' % re.escape(op), text)
        if m:
            line = text.count("\n", 0, m.start()) + 1
            return (FOUND, '%s 命中锚点 name="%s" @行 %d' % (src, op, line))
        return (NOT_FOUND, '%s 无 name="%s" 锚点 → ONNX 不定义此算子名' % (src, op))
    # 来源 3：onnx.com.cn 单算子页面 HTTP 码（独立佐证）
    code = _curl_http_code(ONNX_PAGE.format(op=op))
    if code == "200":
        return (FOUND, "onnx.com.cn/onnx/operators/onnx__%s.html → HTTP 200" % op)
    if code in ("404", "403"):
        return (NOT_FOUND, "onnx.com.cn/onnx/operators/onnx__%s.html → HTTP %s → 无此算子" % (op, code))
    return (UNREACHABLE, "Operators.md 与 onnx.com.cn 均取不到（本地无克隆 + curl 失败）")


def lookup_tflite(op, refs_dir):
    """TFLite 存在性：builtin_ops.h 的 kTfLiteBuiltin<Op> 枚举（精确，不前缀误配）。"""
    text = _read_local(os.path.join(refs_dir, "tensorflow", "tensorflow", "lite", "builtin_ops.h"))
    src = "本地 references/tensorflow/.../builtin_ops.h"
    if text is None:
        text = _curl(TFLITE_RAW)
        src = _LAST_FETCH_URL or TFLITE_RAW
    if text is None:
        return (UNREACHABLE, "builtin_ops.h 取不到（本地无克隆 + curl 失败）")
    # 精确：kTfLiteBuiltinSelect 不会误配 kTfLiteBuiltinSelectV2（后者 Select 后接 V2 而非 =）
    m = re.search(r'kTfLiteBuiltin%s\s*=\s*(\d+)' % re.escape(op), text)
    if m:
        return (FOUND, "%s 命中 kTfLiteBuiltin%s = %s" % (src, op, m.group(1)))
    return (NOT_FOUND, "%s 无 kTfLiteBuiltin%s → TFLite 不定义此 builtin（注意框架命名可能不同，如 Conv→Conv2d）" % (src, op))


def main():
    ap = argparse.ArgumentParser(description="算子框架存在性裁决器（decision1 证据来源）")
    ap.add_argument("--op", required=True, help="算子名（按目标框架的命名，如 Select / Where / SelectV2）")
    ap.add_argument("--framework", choices=["onnx", "tflite", "all"], default="all")
    ap.add_argument("--refs-dir", default=DEFAULT_REFS, help="本地克隆根目录（默认 skill 的 references/）")
    ap.add_argument("--cross-ref", action="store_true",
                    help="只做跨框架映射字典探测（decision2 候选来源④），不做 decision1 存在性裁决")
    args = ap.parse_args()

    if args.cross_ref:
        return cross_ref(args.op, args.refs_dir)

    targets = ["onnx", "tflite"] if args.framework == "all" else [args.framework]
    results = {}
    if "onnx" in targets:
        results["ONNX"] = lookup_onnx(args.op, args.refs_dir)
    if "tflite" in targets:
        results["TFLite"] = lookup_tflite(args.op, args.refs_dir)

    print('== fetch_op_spec: op=%s ==' % args.op)
    for fw, (verdict, evidence) in results.items():
        print("%-7s: %-11s | %s" % (fw, verdict, evidence))

    print("\n可直接粘进 decision4「框架对应关系」表的证据：")
    print("| 框架 | 算子名 | 查证证据（fetch_op_spec 实跑） | 结论 |")
    print("|------|--------|------------------------------|------|")
    for fw, (verdict, evidence) in results.items():
        if verdict == FOUND:
            concl = "有此算子 → 可建 parser/用例"
        elif verdict == NOT_FOUND:
            concl = "**无此算子 → 不建 parser、不造用例**"
        else:
            concl = "**取不到 → 停下问用户，禁止猜**"
        print("| %s | %s | %s | %s |" % (fw, args.op, evidence, concl))

    sem_fetchers = {"ONNX": onnx_semantics, "TFLite": tflite_semantics}
    sem_urls = {"ONNX": ONNX_RAW, "TFLite": "https://tensorflow.google.cn/mlir/tfl_ops"}
    print("\n语义摘要(广播/形状约束——必须据此实现,**禁止凭记忆补**;"
          "尤其非广播版 vs 广播版,差别就在这段):")
    for fw, (verdict, _ev) in results.items():
        if verdict != FOUND:
            continue
        sem = sem_fetchers[fw](args.op)
        if sem:
            print("[%s] %s" % (fw, sem))
        else:
            print("[%s] 语义段未取到 → 必须手动查 %s,**禁止凭记忆判断广播/形状约束**"
                  % (fw, sem_urls[fw]))

    unreachable = [fw for fw, (v, _) in results.items() if v == UNREACHABLE]
    if unreachable:
        print("\n[!] UNREACHABLE: %s —— 走 decision1 兜底向用户索取规格，禁止凭记忆断言其存在与否。"
              % ", ".join(unreachable), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
