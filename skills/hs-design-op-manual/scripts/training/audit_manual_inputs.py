#!/usr/bin/env python3
"""Audit training document facts, current evidence and exact candidate content.

This validates synchronization, not the truth of arbitrary prose or training
numerics. Source review and the training runner remain separate requirements.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys

# One shared drive/WSL resolver, owned by the Host evidence audit.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hs-verify-op-host/scripts/training"))
try:
    from aggregate_training_results import resolve_evidence_path
finally:
    sys.path.pop(0)

DESIGN = {"scope": "规格与前向前置", "backward": "反向传播设计",
          "implementation": "软件实现与复用", "limits": "支持范围与限制"}
REQUIRED_SOURCES = ("docs/forward-prerequisite.md", "docs/backward-contract.md",
                    "docs/train-link-analysis.md", "docs/implementation-contract.md",
                    "docs/generated-code-inspection.md", "scripts/train_case_spec.py")
BASE_CAPABILITIES = ("parser", "selection", "helper")
FREEZE_CAPABILITIES = ("development_chain", "graph", "memory", "export", "freeze_snapshot")
OPTIONAL_CAPABILITIES = ("matmul_kernel_dw_null_check",)
REQUIRED_CAPABILITIES = BASE_CAPABILITIES
REQUIRED_CHECKS = {"package_source_freshness", "target_backward_path",
                   "training_graph_and_memory", "inference_isolation"}
FREEZE_CHECKS = {"development_chain", "training_graph", "training_memory",
                 "weight_export", "freeze_snapshot"}
RESULTS = {"PASS", "FAIL", "NOT_RUN", "BLOCKED", "PASS_EXPECTED_ERROR"}
CAPABILITIES = {"AVAILABLE", "MISSING", "BLOCKED", "NOT_RUN", "NOT_REQUESTED", "UNSUPPORTED"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_id(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]+", value)


def inside(root, relative):
    raw = str(relative)
    if not Path(raw).anchor and not PureWindowsPath(raw).drive:
        # Keep relative-path compatibility; absolute aliases use the shared resolver.
        base = root.resolve()
        path = (base / raw).resolve()
        if not path.is_relative_to(base):
            raise ValueError(f"path outside opdir: {raw}")
        return path
    try:
        return resolve_evidence_path(raw, root)
    except ValueError as exc:
        raise ValueError(f"path outside opdir or invalid evidence path: {relative}: {exc}") from exc


def record(root, item):
    require(isinstance(item, dict), "invalid evidence record")
    p = inside(root, item["path"])
    require(p.is_file() and sha256(p) == item["sha256"], f"missing/changed evidence: {item['path']}")
    return p


def text(value, name):
    require(isinstance(value, str) and value.strip(), f"missing text: {name}")
    require(not any(x in value for x in ("????", "\ufffd", "TODO", "待填写")), f"placeholder: {name}")
    require(not re.search(r"[A-Za-z]:[\\/]|/home/|/mnt/[a-z]/|https?://", value), f"nonpublic path/link: {name}")
    return value


def render(facts):
    """Deterministic candidates; prose lives in reviewed facts design fields."""
    design = [f"# {facts['operator']} 训练算子设计文档", ""]
    for key, title in DESIGN.items():
        design += [f"## {title}", "", facts["design"][key], ""]
    design += ["## 权重冻结能力", "", f"本次要求冻结：{'是' if facts['requires_freezing'] else '否'}。", ""]
    capability_names = (*BASE_CAPABILITIES, *FREEZE_CAPABILITIES,
                        *(name for name in OPTIONAL_CAPABILITIES
                          if name in facts.get("capabilities", {})))
    for name in capability_names:
        design += [f"- {name}：{facts['capabilities'].get(name, 'NOT_REQUESTED')}"]
    design += ["", facts["capability_notes"], "", "## 设计来源", ""]
    design += [f"- `{x['path']}`（SHA256：`{x['sha256']}`）" for x in facts["sources"] if x["path"] in REQUIRED_SOURCES[:4]]
    verify = [f"# {facts['operator']} 训练算子验证文档", "", "## 测试设计", "",
              facts["test_design"], "", "## 本轮结果", "",
              f"运行标识：`{facts['run_id']}`。", "",
              f"Host：**{facts['host_status']}**。{facts['host_reason']}", "",
              f"WS63 板端：**{facts['board_status']}**。{facts['board_reason']}", "",
              "原始梯度：未由默认执行器导出，未进行逐元素梯度比较。参数更新比较不能替代此项。", "",
              "## 逐用例结果", ""]
    for c in facts["expected_cases"]:
        verify += [f"### {c['case_id']}", "", f"测试点：{c['test_point']}",
                   f"类型：`{c['kind']}`。状态：**{c['status']}**。", f"说明：{c['reason'] or '无额外说明'}", ""]
    verify += ["## 结构与来源检查", ""]
    observed = {x["name"]: x for x in facts["checks"]["observed"]}
    for name in facts["checks"]["required"]:
        x = observed[name]
        verify += [f"- {name}：{x['status']}。{x['reason']}"]
    verify += ["", "## 证据索引", ""]
    verify += [f"- `{x['path']}`（SHA256：`{x['sha256']}`）" for x in facts["sources"]]
    return "\n".join(design).rstrip()+"\n", "\n".join(verify).rstrip()+"\n"


def audit_execution(root, summary, locked, case_record, require_freeze=False):
    """Check runner evidence completeness, without recomputing its numerics."""
    require(summary.get("schema_version") == 1, "summary schema_version")
    require(summary.get("case_sha256") == case_record["sha256"], "summary uses different locked case")
    commands = summary.get("commands")
    stages = summary.get("stages")
    evidence = summary.get("evidence")
    require(isinstance(commands, list) and commands, "commands missing")
    require(isinstance(stages, list) and stages, "stages missing")
    require(isinstance(evidence, list) and evidence, "execution evidence missing")
    require(isinstance(summary.get("not_evaluated"), list), "not_evaluated missing")
    expected_commands = (["converter_help", "convert"] if locked["kind"] == "reject"
                       else ["converter_help", "convert", "configure", "build", "benchmark"])
    require([x.get("stage") for x in commands] == expected_commands, "command sequence missing")
    records = {}
    for item in evidence:
        require(isinstance(item, dict), "invalid runner evidence")
        path = Path(item["path"])
        # Preserve native absolute toolchain evidence (which may live outside
        # opdir). Foreign aliases and relative evidence stay confined to opdir;
        # no guessed mapping for inaccessible WSL /home tools on Windows.
        path = (resolve_evidence_path(str(path), Path(path.anchor)) if path.is_absolute()
                else inside(root, item["path"]))
        require(path.is_file() and sha256(path) == item["sha256"], "runner evidence missing/changed")
        require(item.get("bytes") == path.stat().st_size, "runner evidence byte count")
        records[str(path.resolve())] = item
    for command in commands:
        require(isinstance(command.get("argv"), list) and command["argv"] and all(isinstance(x, str) for x in command["argv"]), "command argv")
        require(not command.get("timed_out"), "timed out command cannot pass")
        require(str(inside(root, command["log"])) in records, "command log missing from evidence")
        rc = command.get("exit_code")
        require(type(rc) is int, "command exit code")
        if command.get("stage") == "converter_help":
            require(rc == 0, "converter help probe must succeed")
        elif locked["kind"] == "reject":
            require(1 <= rc < 0xC0000000, "expected rejection command must fail")
        else:
            require(rc == 0, "command must succeed")
    observed = {x.get("stage"): x.get("status") for x in stages}
    if locked["kind"] == "reject":
        require(observed.get("convert") == "PASS_EXPECTED_ERROR", "expected rejection stage missing")
        require(isinstance(locked.get("expected_error"), str) and locked["expected_error"].strip(), "expected diagnostic missing")
        require(locked["expected_error"] in inside(root, commands[1]["log"]).read_text(encoding="utf-8", errors="replace"), "expected diagnostic absent from log")
        return
    require(all(observed.get(x) == "PASS" for x in ("environment", "convert", "build", "training", "numerical")), "execution stage incomplete")
    steps = locked["training"]["steps"]
    require(type(steps) is int and steps >= 2, "locked training steps")
    outputs, weights = locked["outputs"], locked["weights"]
    require(isinstance(outputs, list) and len(outputs) >= 2 and isinstance(weights, list) and weights, "locked outputs/weights missing")
    names = {f"predict/output_{x['index']}" for x in outputs[:-1]}
    for step in (0, 1, steps):
        names |= {f"step_{step}/output_{x['index']}" for x in outputs}
        names |= {f"step_{step}/weight/{x['reference']}" for x in weights}
    for phase in ("before", "after"):
        names |= {f"{phase}/{x['name']}" for x in weights}
    require(locked.get("upstream_weights"), "upstream weights missing")
    names |= {f"upstream_update/{x}" for x in locked["upstream_weights"]}
    frozen_weights = locked.get("frozen_weights", [])
    if require_freeze:
        require(isinstance(frozen_weights, list) and frozen_weights, "frozen weights missing")
    names |= {f"frozen_unchanged/{x}" for x in frozen_weights}
    barrier_weights = locked.get("barrier_weights", [])
    if not isinstance(barrier_weights, list) or not all(isinstance(x, str) and x for x in barrier_weights):
        raise ValueError("invalid barrier weights")
    names |= {f"barrier_unchanged/{x}" for x in barrier_weights}
    if require_freeze:
        require(all(any(x.startswith(prefix + "/") for x in names)
                    for prefix in ("before", "after")), "freeze snapshot evidence missing")
    checks = summary["checks"]
    require(isinstance(checks, list) and len(checks) == len(names) and {x.get("name") for x in checks} == names, "numerical check coverage incomplete")


def validate(root, facts, publication):
    require(facts.get("schema_version") == 1 and facts.get("verification_kind") == "training", "schema/type")
    require(facts.get("publication") == publication, "publication mismatch")
    require(safe_id(facts.get("run_id")) and safe_id(facts.get("operator")), "operator/run_id")
    scope = facts.get("framework_scope")
    require(isinstance(scope, list) and scope and len(scope) == len(set(scope)) and set(scope) <= {"onnx", "tflite"}, "framework_scope")
    require(type(facts.get("requires_freezing")) is bool, "requires_freezing")
    for key in DESIGN:
        text(facts["design"][key], key)
    for key in ("test_design", "host_reason", "board_reason", "capability_notes"):
        text(facts[key], key)
    for name in BASE_CAPABILITIES:
        require(facts["capabilities"].get(name) in CAPABILITIES, f"capability:{name}")
    for name in (*FREEZE_CAPABILITIES, *OPTIONAL_CAPABILITIES):
        if name in facts.get("capabilities", {}):
            require(facts["capabilities"][name] in CAPABILITIES, f"capability:{name}")
    freeze_missing = facts["requires_freezing"] and any(
        facts["capabilities"].get(n) != "AVAILABLE" for n in FREEZE_CAPABILITIES)
    if facts["requires_freezing"] and facts.get("host_status") == "PASS":
        require(all(facts["capabilities"].get(n) == "AVAILABLE" for n in FREEZE_CAPABILITIES),
                "Host PASS requires complete freezing capabilities")
    host = facts["host_status"]
    require(host in {"PASS", "FAIL", "NOT_RUN", "BLOCKED"}, "host_status")
    require(facts["board_status"] in {"PASS", "FAIL", "NOT_RUN", "NOT_REQUESTED", "BLOCKED"}, "board_status")
    require(not freeze_missing or host in {"BLOCKED", "FAIL", "NOT_RUN"}, "missing freezing capability cannot be Host PASS")
    if publication == "initial":
        require(host in {"NOT_RUN", "BLOCKED"} and facts["board_status"] in {"NOT_RUN", "NOT_REQUESTED", "BLOCKED"}, "initial result cannot claim execution")
    sources = facts["sources"]
    require(isinstance(sources, list), "sources")
    paths = [x["path"] for x in sources]
    require(len(paths) == len(set(paths)), "duplicate evidence")
    require(set(REQUIRED_SOURCES) <= set(paths), "required source missing")
    for item in sources:
        require(isinstance(item["path"], str) and not Path(item["path"]).is_absolute() and "\\" not in item["path"] and ":" not in item["path"], "evidence must use relative paths")
        record(root, item)
    source_map = {x["path"]: x for x in sources}
    cases = facts["expected_cases"]
    require(isinstance(cases, list) and cases, "expected_cases")
    ids = [x["case_id"] for x in cases]
    require(all(safe_id(x) for x in ids) and len(ids) == len(set(ids)), "duplicate/invalid case id")
    for c in cases:
        text(c["test_point"], "test_point")
        if c.get("status") == "PASS" and c.get("reason") == "":
            pass  # Real runner success has no diagnostic; do not invent one.
        else:
            text(c["reason"], "reason")
        require(c["status"] in RESULTS and c["kind"] in {"numerical", "reject"}, "case status/kind")
        if publication == "initial":
            require(c["status"] in {"NOT_RUN", "BLOCKED"}, "initial case cannot claim execution")
        require(c["status"] != "PASS_EXPECTED_ERROR" or c["kind"] == "reject", "rejection is not numerical PASS")
        require(c["status"] != "PASS" or c["kind"] == "numerical", "reject case must use PASS_EXPECTED_ERROR")
        rel = f"cases/{c['case_id']}/case.json"
        require(rel in source_map, f"case hash missing: {rel}")
        locked = load(root / rel)
        require(locked.get("verification_kind") == "training", "locked case type")
        require(all(locked.get(k) == c[k] for k in ("case_id", "kind", "test_point")), "locked case identity")
    required = facts["checks"]["required"]
    observed = facts["checks"]["observed"]
    if facts["requires_freezing"] and host == "PASS":
        require(set(REQUIRED_CHECKS) <= set(required), "required checks")
        require(FREEZE_CHECKS <= set(required), "freezing checks")
    require(isinstance(required, list) and len(required) == len(set(required)) and REQUIRED_CHECKS <= set(required), "required checks")
    require(isinstance(observed, list) and len(observed) == len(required), "every check needs status/reason")
    require({x["name"] for x in observed} == set(required), "check names mismatch")
    for x in observed:
        require(x["status"] in {"PASS", "FAIL", "NOT_RUN", "BLOCKED"}, "check status")
        text(x["reason"], "check reason")
        if x["status"] in {"PASS", "FAIL"}:
            require(x.get("evidence") in source_map, "check evidence missing")
        if host == "PASS":
            require(x["status"] == "PASS", "Host PASS missing required check")
    if facts["board_status"] == "PASS":
        require(host == "PASS", "board PASS requires Host PASS")
    if facts["board_status"] in {"PASS", "FAIL"}:
        require(facts.get("board_evidence") in source_map, "board evidence missing")
        board = load(root / facts["board_evidence"])
        require(board.get("verification_kind") == "training" and board.get("run_id") == facts["run_id"] and board.get("status") == facts["board_status"], "board result identity")
    if publication == "final":
        rel = f"runs/{facts['run_id']}/train_verify_summary.json"
        require(rel in source_map, "aggregate hash missing")
        agg = load(root / rel)
        require(agg.get("schema_version") == 1 and agg.get("verification_kind") == "training" and agg.get("run_id") == facts["run_id"] and agg.get("status") == host, "aggregate identity/status")
        rows = agg["cases"]
        require(isinstance(rows, list) and [x["case_id"] for x in rows] == ids, "aggregate case matrix/order")
        for c, row in zip(cases, rows):
            require(all(row.get(k) == c[k] for k in ("case_id", "test_point", "kind", "status", "reason")), "aggregate case content")
            summary_rel = f"runs/{facts['run_id']}/{c['case_id']}/train_summary.json"
            require(row["summary"]["path"] == summary_rel and summary_rel in source_map, "summary path/hash missing")
            require(row["summary"] == source_map[summary_rel], "summary hash mismatch")
            s = load(record(root, row["summary"]))
            require(s.get("run_id") == facts["run_id"] and s.get("verification_kind") == "training", "summary identity")
            require(all(s.get(k) == c[k] for k in ("case_id", "test_point", "kind", "status")), "summary content/status")
            if c["status"] in {"PASS", "PASS_EXPECTED_ERROR"}:
                case_rel = f"cases/{c['case_id']}/case.json"
                audit_execution(root, s, load(root / case_rel), source_map[case_rel], facts["requires_freezing"] and host == "PASS")
            if c["status"] == "PASS":
                require(s.get("numerical_pass") is True and s.get("checks") and all(x.get("status") == "PASS" for x in s["checks"]), "numerical evidence missing")
            else:
                require(s.get("numerical_pass") is False, "non-PASS cannot claim numerical pass")
        if host == "PASS":
            require(any(c["kind"] == "numerical" for c in cases), "no numerical cases")
            require(all(c["status"] == ("PASS" if c["kind"] == "numerical" else "PASS_EXPECTED_ERROR") for c in cases), "incomplete Host matrix")
        if any(c["status"] == "FAIL" for c in cases):
            require(host == "FAIL", "case FAIL must remain aggregate FAIL")


def audit(opdir, facts_path, design, verify, publication):
    try:
        root = Path(opdir).resolve()
        fp = inside(root, str(facts_path))
        facts = load(fp)
        validate(root, facts, publication)
        require(design is not None and verify is not None, "both document candidates required")
        dp, vp = inside(root, str(design)), inside(root, str(verify))
        require(len({dp, vp, fp}) == 3, "document paths overlap")
        expected = render(facts)
        for p, content in zip((dp, vp), expected):
            require(p.read_text(encoding="utf-8").replace("\r\n", "\n") == content, f"candidate content mismatch: {p.name}")
        return "PASS", []
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return "FAIL", [str(exc)]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--opdir", type=Path, required=True)
    p.add_argument("--facts", required=True)
    p.add_argument("--design", required=True)
    p.add_argument("--verify", required=True)
    p.add_argument("--publication", choices=("initial", "final"), required=True)
    p.add_argument("--render-candidates", action="store_true", help="Create new candidates only; never publish or overwrite.")
    args = p.parse_args(argv)
    try:
        if args.render_candidates:
            root = args.opdir.resolve()
            facts = load(inside(root, str(args.facts)))
            validate(root, facts, args.publication)
            paths = [inside(root, str(x)) for x in (args.design, args.verify)]
            require(len(set(paths)) == 2 and all(not x.exists() and x.parent == root / "docs" for x in paths), "new candidates must be distinct files under opdir/docs")
            for path, content in zip(paths, render(facts)):
                with path.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(content)
        status, issues = audit(args.opdir, args.facts, args.design, args.verify, args.publication)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        status, issues = "FAIL", [str(exc)]
    print(f"TRAIN_MANUAL_STATUS={status}")
    print("TRAIN_MANUAL_ISSUES=" + json.dumps(issues, ensure_ascii=False))
    print(f"TRAIN_MANUAL_FACTS_SYNC={status}")
    print(f"TRAIN_MANUAL_CONTENT_SYNC={status}")
    print(f"TRAIN_MANUAL_CASE_SYNC={status}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
