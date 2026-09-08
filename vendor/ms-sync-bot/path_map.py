#!/usr/bin/env python3
"""A→B 路径映射（方案 §4.2）：

仅取 A 仓 src/mindspore-lite/ 前缀下的路径，去掉前缀后折叠连续重复段
（A 子集目录由同步脚本复制产生 a/a/ 形态，如 tools/tools、src/src）。

实测依据（2026-08-29）：A 子集 5662 文件映射后 5640 个与 B 逐字节一致（99.6%）。
"""
import fnmatch

INCLUDE_PREFIX = "src/mindspore-lite/"

# 前缀之外的整体不同步（C 部分与无关内容）
EXCLUDE_PREFIXES = ("src/adaptor/", "src/samples/", "patch/", "docs/")

# 折叠后路径上的忽略规则（fnmatch，相对 B 根）
IGNORE_RULES = [
    "cmake/external_libs/opencl.cmake",        # §8.3 A 侧历史残留
    "cmake/external_libs/openssl copy.cmake",  # 垃圾副本
]

# 生成物默认不同步（§4.2：由 B 侧构建时重新生成，避免生成器版本差异）
GENERATED_RULES = ["*_generated.h", "*_generated.cc", "*.gen.h", "*.gen.cc"]

ACTION_MAP = "map"
ACTION_IGNORE = "ignore"
ACTION_GENERATED = "generated"


def collapse_duplicate_segments(path: str) -> str:
    """折叠连续重复段：a/a/b -> a/b，循环应用直到不再变化。"""
    parts = path.split("/")
    out = []
    for p in parts:
        if out and out[-1] == p:
            continue
        out.append(p)
    return "/".join(out)


def map_path(a_path: str):
    """A 仓相对路径 → (b_path 或 None, action, reason)。

    action: map       正常映射，参与同步
            ignore    不同步（前缀外/忽略规则）
            generated 生成物，不同步但单独打标
    """
    if not a_path.startswith(INCLUDE_PREFIX):
        for pre in EXCLUDE_PREFIXES:
            if a_path.startswith(pre):
                return None, ACTION_IGNORE, "excluded dir (%s)" % pre
        return None, ACTION_IGNORE, "not under %s" % INCLUDE_PREFIX

    rel = a_path[len(INCLUDE_PREFIX):]
    b_path = collapse_duplicate_segments(rel)

    if any(fnmatch.fnmatch(b_path, pat) for pat in IGNORE_RULES):
        return None, ACTION_IGNORE, "ignore_forever (protected_files.yaml)"

    if any(fnmatch.fnmatch(b_path, pat) for pat in GENERATED_RULES):
        return None, ACTION_GENERATED, "generated artifact, rebuild on B"

    return b_path, ACTION_MAP, ""


def map_hunk_path(a_path: str):
    """diff 头中的 hunk 路径（可能带 b/ a/ 前缀之外的引号转义）暂时与 map_path 一致。"""
    return map_path(a_path)


if __name__ == "__main__":
    # 自测：覆盖已验证的映射样例与过滤规则
    cases = [
        # (A路径, 期望B路径或None, 期望action)
        ("src/mindspore-lite/mindspore-lite/tools/tools/converter/micro/coder/opcoders/nnacl/int8/fill_int8_coder.cc",
         "mindspore-lite/tools/converter/micro/coder/opcoders/nnacl/int8/fill_int8_coder.cc", ACTION_MAP),
        ("src/mindspore-lite/mindspore-lite/src/src/litert/kernel/cpu/int8/softplus_int8.cc",
         "mindspore-lite/src/litert/kernel/cpu/int8/softplus_int8.cc", ACTION_MAP),
        ("src/mindspore-lite/cmake/cmake/external_libs/flatbuffers.cmake",
         "cmake/external_libs/flatbuffers.cmake", ACTION_MAP),
        ("src/mindspore-lite/cmake/cmake/external_libs/opencl.cmake", None, ACTION_IGNORE),
        ("src/mindspore-lite/cmake/cmake/external_libs/openssl copy.cmake", None, ACTION_IGNORE),
        ("src/adaptor/adaptor/cpu/foo.cc", None, ACTION_IGNORE),
        ("src/samples/x/y.py", None, ACTION_IGNORE),
        ("patch/129.diff", None, ACTION_IGNORE),
        ("docs/README.md", None, ACTION_IGNORE),
        ("src/mindspore-lite/mindspore-lite/schema/schema/ops_generated.h",
         None, ACTION_GENERATED),
        ("src/mindspore-lite/build.sh", "build.sh", ACTION_MAP),
    ]
    failed = 0
    for a, want_b, want_act in cases:
        b, act, reason = map_path(a)
        ok = (b == want_b and act == want_act)
        if not ok:
            failed += 1
        print("%s %-70s -> %-60s %s %s" % ("PASS" if ok else "FAIL", a[:70], b, act, reason))
    # 三层重复也应折叠干净
    t = collapse_duplicate_segments("a/a/a/b/b/c")
    print("collapse a/a/a/b/b/c ->", t, "(expect a/b/c)")
    if t != "a/b/c":
        failed += 1
    print("result:", "ALL PASS" if failed == 0 else "%d FAILED" % failed)
    raise SystemExit(0 if failed == 0 else 1)
