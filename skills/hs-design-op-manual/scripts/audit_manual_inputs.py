#!/usr/bin/env python3
"""Audit whether operator inputs are safe and synchronized for manual publication."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


CORE_SOURCES = (
    Path("docs/spec.md"),
    Path("docs/implementation-contract.md"),
    Path("scripts/capability_checklist.json"),
    Path("scripts/op_spec.py"),
)
CASE_ASSIGNMENTS = ("ONNX_TEST_CASES", "TFLITE_TEST_CASES")
OP_NAME_ASSIGNMENT = "OP_NAME"
CONTRACT_KEYS = (
    "source_entries",
    "primitive_type",
    "input_contract",
    "optional_inputs",
    "attribute_contract",
    "layout_contract",
    "dtype_contract",
    "output_contract",
    "verification_mode",
    "unsupported_or_deferred",
)
MANUAL_CASE_SECTION = re.compile(
    r"^###\s+4(?:[-.]2)\b[^\n]*\n(?P<body>.*?)(?=^#{1,3}\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
MANUAL_SCENARIO_SECTION = re.compile(
    r"^##\s+3\.\s+关键场景分析\s*\n(?P<body>.*?)(?=^##\s+4\.|\Z)",
    re.MULTILINE | re.DOTALL,
)
MANUAL_CASE_ROW = re.compile(r"^\s*\|\s*(TC-\d{3,})\s*\|", re.MULTILINE)
MANUAL_CASE_HEADERS = (
    "用例编号",
    "框架/source entry",
    "模型 dtype",
    "已覆盖运行通路",
    "input_shape",
    "输入数据特征（value_domain）",
    "算子属性",
    "预期输出",
)
MANUAL_SCENARIO_HEADERS = (
    "使用场景",
    "什么时候会遇到",
    "已覆盖行为与限制",
    "对应用例",
)
COVERAGE_PRINCIPLE_QUESTIONS = (
    "输入是否覆盖常见规模？",
    "不同选择方式是否正确？",
    "边界和数据内容是否覆盖？",
    "量化/非量化通路是否覆盖？",
)
INTERNAL_VERIFICATION_PATH_NAMES = (
    "x86_fp32",
    "riscv_fp32",
    "riscv_int8",
)
MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
MARKDOWN_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")
MARKDOWN_SEPARATOR_CELL = re.compile(r"^\s*:?-{3,}:?\s*$")
FAIL_COUNT = re.compile(r"\b(\d+)\s+FAIL(?:S|ED|URES?)?\b", re.IGNORECASE)
ERR_COUNT = re.compile(r"\b(\d+)\s+ERR(?:OR)?S?\b", re.IGNORECASE)
CAPABILITY_COUNT = re.compile(r"\bcapabilities=(\d+)/(\d+)\b", re.IGNORECASE)
HARNESS_EXIT = re.compile(r"^\s*HARNESS_EXIT=(-?\d+)\s*$", re.MULTILINE)
VERDICT_OP = re.compile(r"\bop=([A-Za-z0-9_]+)\b")
SUMMARY_CASE_ROW = re.compile(
    r"^(onnx|tflite)\s+tc(\d+)\s+([A-Za-z0-9_]+)\s+(PASS|FAIL|ERR)\b",
    re.MULTILINE | re.IGNORECASE,
)
FINAL_PLACEHOLDERS = ("未记录", "待确认", "尚未执行验证")
CASE_PARAM_COLUMNS = frozenset(("shape", "dtype", "value_domain"))


@dataclass(frozen=True)
class CaseDiff:
    missing: frozenset[str]
    extra: frozenset[str]
    duplicates: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SummaryState:
    failing: bool
    trustworthy_success: bool
    operator: str | None
    capability_covered: int | None
    capability_total: int | None


@dataclass(frozen=True)
class OpCase:
    case_id: str
    framework: str
    description: str
    params: dict[str, object]


@dataclass(frozen=True)
class OpSpecState:
    operator: str
    cases: tuple[OpCase, ...]
    frameworks: frozenset[str]

    @property
    def case_ids(self) -> tuple[str, ...]:
        return tuple(case.case_id for case in self.cases)


@dataclass(frozen=True)
class ChecklistState:
    operator: str
    frameworks: frozenset[str]
    capability_count: int
    covered_case_ids: frozenset[str]
    current_schema: bool


@dataclass(frozen=True)
class ContentDiff:
    mismatches: frozenset[str]


@dataclass(frozen=True)
class FactsAudit:
    facts_sync: bool
    content_sync: bool | None
    publishable: bool
    issues: frozenset[str]
    content_mismatches: frozenset[str] = frozenset()


def _normalize_case_id(value: object) -> str:
    if isinstance(value, bool):
        raise ValueError("boolean case IDs are not supported")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        text = value.strip()
        if text.upper().startswith("TC-"):
            text = text[3:]
        if not text.isdigit():
            raise ValueError(f"unsupported case ID: {value!r}")
        number = int(text)
    else:
        raise ValueError(f"unsupported case ID: {value!r}")
    if number < 0:
        raise ValueError(f"negative case ID: {value!r}")
    return f"TC-{number:03d}"


def _resolve_core_sources(opdir: Path | str) -> tuple[Path, dict[Path, Path]]:
    root = Path(opdir).resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"opdir is not a directory: {root}")

    sources: dict[Path, Path] = {}
    for relative in CORE_SOURCES:
        resolved = (root / relative).resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"core source escapes opdir: {relative}") from exc
        if not resolved.is_file():
            raise ValueError(f"core source is not a regular file: {relative}")
        sources[relative] = resolved
    return root, sources


def _literal_assignments(source: str, filename: str) -> dict[str, object]:
    tree = ast.parse(source, filename=filename)
    assignments: dict[str, object] = {}
    for node in tree.body:
        targets: Iterable[ast.expr]
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
            value = node.value
        else:
            continue
        if value is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id in (
                *CASE_ASSIGNMENTS,
                OP_NAME_ASSIGNMENT,
            ):
                assignments[target.id] = ast.literal_eval(value)
    return assignments


def parse_op_spec(path: Path | str) -> OpSpecState:
    spec_path = Path(path)
    assignments = _literal_assignments(
        spec_path.read_text(encoding="utf-8"), str(spec_path)
    )
    operator = assignments.get(OP_NAME_ASSIGNMENT)
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("OP_NAME must be a non-empty literal string")

    parsed_cases: list[OpCase] = []
    frameworks: set[str] = set()
    for name in CASE_ASSIGNMENTS:
        cases = assignments.get(name)
        if not isinstance(cases, (list, tuple)):
            raise ValueError(f"{name} must be a literal list or tuple")
        framework = name.removesuffix("_TEST_CASES").lower()
        if cases:
            frameworks.add(framework)
        for case in cases:
            if not isinstance(case, dict) or "id" not in case:
                raise ValueError(f"{name} contains a case without an id")
            params = case.get("params", {})
            if not isinstance(params, dict):
                raise ValueError(f"{name} case params must be a literal object")
            description = case.get("desc", "")
            if not isinstance(description, str):
                raise ValueError(f"{name} case desc must be a string")
            parsed_cases.append(
                OpCase(
                    case_id=_normalize_case_id(case["id"]),
                    framework=framework,
                    description=description.strip(),
                    params=params,
                )
            )
    duplicates = {
        case_id
        for case_id, count in Counter(
            case.case_id for case in parsed_cases
        ).items()
        if count != 1
    }
    if duplicates:
        raise ValueError(f"duplicate op_spec case IDs: {sorted(duplicates)}")
    if not parsed_cases or not frameworks:
        raise ValueError("op_spec must contain at least one framework case")
    return OpSpecState(
        operator=operator.strip(),
        cases=tuple(parsed_cases),
        frameworks=frozenset(frameworks),
    )


def parse_op_spec_case_ids(path: Path | str) -> frozenset[str]:
    return frozenset(parse_op_spec(path).case_ids)


def _markdown_table_blocks(text: str) -> tuple[tuple[str, ...], ...]:
    blocks: list[tuple[str, ...]] = []
    current: list[str] = []
    for line in text.splitlines():
        if MARKDOWN_TABLE_LINE.fullmatch(line):
            current.append(line)
        elif current:
            blocks.append(tuple(current))
            current = []
    if current:
        blocks.append(tuple(current))
    return tuple(blocks)


def _is_valid_markdown_table(block: tuple[str, ...]) -> bool:
    if len(block) < 2:
        return False
    header_cells = block[0].strip().strip("|").split("|")
    separator_cells = block[1].strip().strip("|").split("|")
    if len(header_cells) != len(separator_cells) or not header_cells:
        return False
    if not all(
        MARKDOWN_SEPARATOR_CELL.fullmatch(cell)
        for cell in separator_cells
    ):
        return False
    return all(
        len(line.strip().strip("|").split("|")) == len(header_cells)
        for line in block[2:]
    )


def _markdown_cells(line: str) -> tuple[str, ...]:
    return tuple(
        cell.strip() for cell in line.strip().strip("|").split("|")
    )


def parse_manual_case_id_sequence(path: Path | str) -> tuple[str, ...]:
    text = Path(path).read_text(encoding="utf-8")
    sections = list(MANUAL_CASE_SECTION.finditer(text))
    if len(sections) > 1:
        raise ValueError("manual must contain exactly one Chapter 4-2 section")
    if not sections:
        return ()
    table_blocks = _markdown_table_blocks(sections[0].group("body"))
    if len(table_blocks) != 1 or not _is_valid_markdown_table(table_blocks[0]):
        raise ValueError(
            "Chapter 4-2 must contain exactly one valid Markdown table"
        )
    table_body = "\n".join(table_blocks[0][2:])
    return tuple(
        _normalize_case_id(case_id)
        for case_id in MANUAL_CASE_ROW.findall(table_body)
    )


def parse_manual_case_ids(path: Path | str) -> frozenset[str]:
    return frozenset(parse_manual_case_id_sequence(path))


def parse_manual_case_table(path: Path | str) -> dict[str, tuple[str, ...]]:
    text = Path(path).read_text(encoding="utf-8")
    sections = list(MANUAL_CASE_SECTION.finditer(text))
    if len(sections) != 1:
        raise ValueError("manual must contain exactly one Chapter 4-2 section")
    table_blocks = _markdown_table_blocks(sections[0].group("body"))
    if len(table_blocks) != 1 or not _is_valid_markdown_table(table_blocks[0]):
        raise ValueError(
            "Chapter 4-2 must contain exactly one valid Markdown table"
        )

    header = _markdown_cells(table_blocks[0][0])
    if header != MANUAL_CASE_HEADERS:
        raise ValueError(
            "Chapter 4-2 table headers do not match the publication schema"
        )

    result: dict[str, tuple[str, ...]] = {}
    for line in table_blocks[0][2:]:
        row = _markdown_cells(line)
        case_id = _normalize_case_id(row[0])
        if case_id in result:
            raise ValueError(f"duplicate manual case ID: {case_id}")
        result[case_id] = row
    return result


def parse_manual_scenario_table(
    path: Path | str,
) -> tuple[tuple[str, ...], ...]:
    text = Path(path).read_text(encoding="utf-8")
    sections = list(MANUAL_SCENARIO_SECTION.finditer(text))
    if len(sections) != 1:
        raise ValueError("manual must contain exactly one Chapter 3 section")
    table_blocks = _markdown_table_blocks(sections[0].group("body"))
    if len(table_blocks) != 1 or not _is_valid_markdown_table(table_blocks[0]):
        raise ValueError(
            "Chapter 3 must contain exactly one valid Markdown table"
        )
    header = _markdown_cells(table_blocks[0][0])
    if header != MANUAL_SCENARIO_HEADERS:
        raise ValueError(
            "Chapter 3 table headers do not match the publication schema"
        )
    return tuple(
        _markdown_cells(line) for line in table_blocks[0][2:]
    )


def parse_case_verification_paths(
    summary_path: Path | str,
) -> dict[str, tuple[str, ...]]:
    path = Path(summary_path)
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    paths: dict[str, list[str]] = {}
    for _, case_id, verification_path, status in SUMMARY_CASE_ROW.findall(text):
        if status.upper() != "PASS":
            continue
        normalized = _normalize_case_id(case_id)
        case_paths = paths.setdefault(normalized, [])
        if verification_path not in case_paths:
            case_paths.append(verification_path)
    return {
        case_id: tuple(case_paths)
        for case_id, case_paths in paths.items()
    }


def _public_verification_coverage(fact_case: dict[str, object]) -> str:
    paths = fact_case.get("verification_paths")
    if not isinstance(paths, list) or not paths:
        return "尚未执行验证"
    dtype = str(fact_case.get("model_dtype", ""))
    integer_dtype = bool(re.fullmatch(r"u?int\d+", dtype))
    labels: list[str] = []
    for path in paths:
        if path == "x86_fp32":
            label = (
                f"x86 主机原生 {dtype}"
                if integer_dtype
                else "x86 主机非量化"
            )
        elif path == "riscv_fp32":
            label = (
                f"RISC-V 原生 {dtype}"
                if integer_dtype
                else "RISC-V 非量化"
            )
        elif path == "riscv_int8":
            label = (
                f"RISC-V 原生 {dtype}"
                if integer_dtype
                else "RISC-V 全量化 int8"
            )
        else:
            label = "其他已验证运行通路"
        if label not in labels:
            labels.append(label)
    return "、".join(labels)


def _safe_source_path(opdir: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError("facts source path must be a non-empty string")
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise ValueError("facts source path must be relative to opdir")
    resolved = (opdir / relative_path).resolve(strict=True)
    try:
        resolved.relative_to(opdir)
    except ValueError as exc:
        raise ValueError(f"facts source escapes opdir: {relative}") from exc
    if not resolved.is_file():
        raise ValueError(f"facts source is not a regular file: {relative}")
    return resolved


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_facts(path: Path | str) -> dict[str, object]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("operator manual facts must be a JSON object")
    return data


def _canonical_attributes(attributes: object) -> str:
    if not isinstance(attributes, dict):
        raise ValueError("case attributes must be a JSON object")
    return "; ".join(
        f"{key}={json.dumps(value, ensure_ascii=False).lower()}"
        for key, value in attributes.items()
    )


def _expected_case_attributes(params: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in params.items()
        if key not in CASE_PARAM_COLUMNS
    }


def _validate_evidence(
    opdir: Path,
    evidence: object,
    *,
    issue_prefix: str,
    issues: set[str],
) -> dict[str, object] | None:
    if not isinstance(evidence, dict):
        issues.add(f"{issue_prefix}:evidence")
        return None
    source = evidence.get("source")
    quote = evidence.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        issues.add(f"{issue_prefix}:evidence-quote")
        return evidence
    try:
        source_path = _safe_source_path(opdir, source)
        source_text = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError):
        issues.add(f"{issue_prefix}:evidence-source")
        return evidence
    if quote not in source_text:
        issues.add(f"{issue_prefix}:evidence-quote")
    return evidence


def _validate_expected_outputs(
    opdir: Path,
    op_case: OpCase,
    fact_case: dict[str, object],
    issues: set[str],
) -> None:
    prefix = f"{op_case.case_id}:expected_outputs"
    outputs = fact_case.get("expected_outputs")
    text = fact_case.get("expected_outputs_text")
    if not isinstance(outputs, list) or not outputs:
        issues.add(prefix)
        return
    if not isinstance(text, str) or not text.strip():
        issues.add(prefix)

    evidence = _validate_evidence(
        opdir,
        fact_case.get("expected_output_evidence"),
        issue_prefix=prefix,
        issues=issues,
    )
    if not evidence:
        return
    shape_rule = evidence.get("shape_rule")
    if shape_rule == "replace_axis_with_k":
        shape = op_case.params.get("shape")
        axis = op_case.params.get("axis")
        k = op_case.params.get("k")
        if (
            not isinstance(shape, list)
            or not shape
            or not isinstance(axis, int)
            or isinstance(axis, bool)
            or not isinstance(k, int)
            or isinstance(k, bool)
        ):
            issues.add(f"{prefix}:shape-rule")
            return
        expected_shape = list(shape)
        try:
            expected_shape[axis % len(expected_shape)] = k
        except (IndexError, ZeroDivisionError):
            issues.add(f"{prefix}:shape-rule")
            return
        for output in outputs:
            if (
                not isinstance(output, dict)
                or not isinstance(output.get("name"), str)
                or output.get("shape") != expected_shape
                or (
                    not isinstance(output.get("dtype"), str)
                    and output.get("dtype_rule") != "same_as_input"
                )
            ):
                issues.add(prefix)
                return
    elif shape_rule != "op_spec_explicit":
        issues.add(f"{prefix}:shape-rule")


def _validate_facts(
    opdir: Path | str,
    facts_path: Path | str,
    *,
    publication: str,
) -> tuple[dict[str, object], set[str]]:
    root, sources = _resolve_core_sources(opdir)
    facts = _load_facts(facts_path)
    issues: set[str] = set()

    if facts.get("schema_version") != 1:
        issues.add("schema_version")
    if facts.get("mode") not in {
        "integrated-final",
        "legacy-sync",
    }:
        issues.add("mode")
    if publication == "final":
        if facts.get("provenance") != "production":
            issues.add("provenance")
        if facts.get("production_eligible") is not True:
            issues.add("production_eligible")

    op_spec = parse_op_spec(sources[Path("scripts/op_spec.py")])
    if facts.get("operator") != op_spec.operator:
        issues.add("operator")

    expected_source_entries = {
        "spec": Path("docs/spec.md"),
        "implementation_contract": Path("docs/implementation-contract.md"),
        "capability_checklist": Path("scripts/capability_checklist.json"),
        "op_spec": Path("scripts/op_spec.py"),
    }
    if publication == "final":
        expected_source_entries["verification_summary"] = Path(
            "verify_summary.txt"
        )
    fact_sources = facts.get("sources")
    if not isinstance(fact_sources, dict):
        issues.add("sources")
        fact_sources = {}
    for name, relative in expected_source_entries.items():
        entry = fact_sources.get(name)
        if not isinstance(entry, dict) or entry.get("path") != str(relative):
            issues.add(f"sources:{name}")
            continue
        try:
            source_path = _safe_source_path(root, entry.get("path"))
        except (OSError, ValueError):
            issues.add(f"sources:{name}")
            continue
        if entry.get("sha256") != _sha256(source_path):
            issues.add(f"sources:{name}:sha256")

    summary_paths = parse_case_verification_paths(root / "verify_summary.txt")
    fact_cases = facts.get("cases")
    if not isinstance(fact_cases, list):
        issues.add("cases")
        fact_cases = []
    if len(fact_cases) != len(op_spec.cases):
        issues.add("cases:count")
    for index, op_case in enumerate(op_spec.cases):
        if index >= len(fact_cases) or not isinstance(fact_cases[index], dict):
            issues.add(f"{op_case.case_id}:missing")
            continue
        fact_case = fact_cases[index]
        expected_fields = {
            "id": op_case.case_id,
            "framework": op_case.framework,
            "model_dtype": op_case.params.get("dtype"),
            "input_shape": op_case.params.get("shape"),
            "value_domain": op_case.params.get("value_domain"),
            "attributes": _expected_case_attributes(op_case.params),
            "verification_paths": list(summary_paths.get(op_case.case_id, ())),
        }
        for field, expected in expected_fields.items():
            if fact_case.get(field) != expected:
                issues.add(f"{op_case.case_id}:{field}")
        if not isinstance(
            fact_case.get("framework_source_entry"), str
        ) or not fact_case.get("framework_source_entry", "").strip():
            issues.add(f"{op_case.case_id}:framework_source_entry")
        _validate_expected_outputs(root, op_case, fact_case, issues)

    checklist = parse_capability_checklist(
        sources[Path("scripts/capability_checklist.json")]
    )
    expected_capabilities = json.loads(
        sources[Path("scripts/capability_checklist.json")].read_text(
            encoding="utf-8"
        )
    )["capabilities"]
    normalized_capabilities = []
    for capability in expected_capabilities:
        normalized_capabilities.append(
            {
                "id": capability.get("id"),
                "description": capability.get("desc"),
                "covered_by": [
                    _normalize_case_id(case_id)
                    for case_id in capability.get("covered_by", [])
                ],
            }
        )
    fact_capabilities = facts.get("capabilities")
    if (
        not isinstance(fact_capabilities, list)
        or len(fact_capabilities) != len(normalized_capabilities)
    ):
        issues.add("capabilities")
    else:
        for expected, actual in zip(
            normalized_capabilities, fact_capabilities
        ):
            if (
                not isinstance(actual, dict)
                or any(actual.get(key) != value for key, value in expected.items())
                or (
                    "manual_text" in actual
                    and (
                        not isinstance(actual["manual_text"], str)
                        or not actual["manual_text"].strip()
                    )
                )
            ):
                issues.add("capabilities")
                break

    capability_by_id = {
        capability["id"]: capability for capability in normalized_capabilities
    }
    scenario_groups = facts.get("scenario_groups")
    if scenario_groups is None:
        scenario_groups = []
    if not isinstance(scenario_groups, list):
        issues.add("scenario_groups")
        scenario_groups = []
    if len(normalized_capabilities) > 7 and not 3 <= len(scenario_groups) <= 7:
        issues.add("scenario_groups:count")
    grouped_capability_ids: list[str] = []
    for group in scenario_groups:
        if not isinstance(group, dict):
            issues.add("scenario_groups:fields")
            continue
        if any(
            not isinstance(group.get(field), str)
            or not group.get(field, "").strip()
            for field in ("title", "when", "behavior")
        ):
            issues.add("scenario_groups:fields")
        capability_ids = group.get("capability_ids")
        if (
            not isinstance(capability_ids, list)
            or any(
                not isinstance(capability_id, str)
                for capability_id in capability_ids
            )
        ):
            issues.add("scenario_groups:partition")
            continue
        grouped_capability_ids.extend(capability_ids)
        expected_covered_by: list[str] = []
        for capability_id in capability_ids:
            capability = capability_by_id.get(capability_id)
            if capability is None:
                issues.add("scenario_groups:partition")
                continue
            for case_id in capability["covered_by"]:
                if case_id not in expected_covered_by:
                    expected_covered_by.append(case_id)
        if group.get("covered_by") != expected_covered_by:
            issues.add("scenario_groups:covered_by")
    if scenario_groups:
        grouped_counts = Counter(grouped_capability_ids)
        if (
            frozenset(grouped_counts) != frozenset(capability_by_id)
            or any(count != 1 for count in grouped_counts.values())
        ):
            issues.add("scenario_groups:partition")

    coverage_principles = facts.get("coverage_principles")
    if not isinstance(coverage_principles, list) or len(coverage_principles) != 4:
        issues.add("coverage_principles")
    else:
        for principle in coverage_principles:
            if (
                not isinstance(principle, dict)
                or any(
                    not isinstance(principle.get(field), str)
                    or not principle.get(field, "").strip()
                    for field in ("question", "answer")
                )
            ):
                issues.add("coverage_principles")
                break
        if tuple(
            principle.get("question")
            for principle in coverage_principles
            if isinstance(principle, dict)
        ) != COVERAGE_PRINCIPLE_QUESTIONS:
            issues.add("coverage_principles:questions")

    if not checklist.covered_case_ids.issubset(frozenset(op_spec.case_ids)):
        issues.add("capabilities:covered_by")

    chapter_facts = facts.get("chapter_facts")
    if not isinstance(chapter_facts, list):
        issues.add("chapter_facts")
        chapter_facts = []
    chapters: set[int] = set()
    for index, chapter_fact in enumerate(chapter_facts):
        prefix = f"chapter_facts:{index}"
        if not isinstance(chapter_fact, dict):
            issues.add(prefix)
            continue
        chapter = chapter_fact.get("chapter")
        if isinstance(chapter, int) and not isinstance(chapter, bool):
            chapters.add(chapter)
        else:
            issues.add(f"{prefix}:chapter")
        if not isinstance(
            chapter_fact.get("manual_text"), str
        ) or not chapter_fact.get("manual_text", "").strip():
            issues.add(f"{prefix}:manual_text")
        _validate_evidence(
            root,
            {
                "source": chapter_fact.get("source"),
                "quote": chapter_fact.get("quote"),
            },
            issue_prefix=prefix,
            issues=issues,
        )
    if publication == "final" and not {1, 2}.issubset(chapters):
        issues.add("chapter_facts:coverage")
    return facts, issues


def compare_manual_content(
    opdir: Path | str,
    facts_path: Path | str,
    manual: Path | str,
) -> ContentDiff:
    del opdir
    facts = _load_facts(facts_path)
    manual_path = Path(manual)
    manual_text = manual_path.read_text(encoding="utf-8")
    manual_cases = parse_manual_case_table(manual_path)
    mismatches: set[str] = set()
    expected_title = f"# {facts.get('operator', '')} 算子设计文档"
    first_line = manual_text.splitlines()[0].strip() if manual_text else ""
    if first_line != expected_title:
        mismatches.add("document_title")
    if any(
        path_name in manual_text
        for path_name in INTERNAL_VERIFICATION_PATH_NAMES
    ):
        mismatches.add("internal_verification_path_names")

    fact_cases = facts.get("cases")
    if not isinstance(fact_cases, list):
        raise ValueError("facts cases must be a list")
    for fact_case in fact_cases:
        if not isinstance(fact_case, dict):
            raise ValueError("facts case must be a JSON object")
        case_id = _normalize_case_id(fact_case.get("id"))
        row = manual_cases.get(case_id)
        if row is None:
            continue
        expected = {
            "framework_source_entry": str(
                fact_case.get("framework_source_entry", "")
            ),
            "model_dtype": str(fact_case.get("model_dtype", "")),
            "verification_paths": _public_verification_coverage(fact_case),
            "input_shape": json.dumps(
                fact_case.get("input_shape"), ensure_ascii=False
            ),
            "value_domain": str(fact_case.get("value_domain", "")),
            "attributes": _canonical_attributes(
                fact_case.get("attributes")
            ),
            "expected_outputs": str(
                fact_case.get("expected_outputs_text", "")
            ),
        }
        actual = {
            "framework_source_entry": row[1],
            "model_dtype": row[2],
            "verification_paths": row[3],
            "input_shape": row[4],
            "value_domain": row[5],
            "attributes": row[6],
            "expected_outputs": row[7],
        }
        for field, expected_value in expected.items():
            if actual[field] != expected_value:
                mismatches.add(f"{case_id}:{field}")

    for index, chapter_fact in enumerate(facts.get("chapter_facts", [])):
        if not isinstance(chapter_fact, dict):
            continue
        manual_fact = chapter_fact.get("manual_text")
        if isinstance(manual_fact, str) and manual_fact not in manual_text:
            mismatches.add(f"chapter_facts:{index}")

    scenario_groups = facts.get("scenario_groups", [])
    if scenario_groups:
        scenario_rows = parse_manual_scenario_table(manual_path)
        if len(scenario_rows) != len(scenario_groups):
            mismatches.add("scenario_groups:count")
        for index, group in enumerate(scenario_groups):
            if not isinstance(group, dict):
                continue
            expected_row = (
                str(group.get("title", "")),
                str(group.get("when", "")),
                str(group.get("behavior", "")),
                ", ".join(group.get("covered_by", [])),
            )
            if index >= len(scenario_rows) or scenario_rows[index] != expected_row:
                mismatches.add(f"scenario_groups:{index}")
    else:
        for capability in facts.get("capabilities", []):
            if not isinstance(capability, dict):
                continue
            capability_id = capability.get("id", "unknown")
            description = capability.get(
                "manual_text", capability.get("description")
            )
            if isinstance(description, str) and description not in manual_text:
                mismatches.add(f"capability:{capability_id}:description")
            for case_id in capability.get("covered_by", []):
                if str(case_id) not in manual_text:
                    mismatches.add(f"capability:{capability_id}:covered_by")

    for index, principle in enumerate(
        facts.get("coverage_principles", [])
    ):
        if not isinstance(principle, dict):
            continue
        question = principle.get("question")
        answer = principle.get("answer")
        if (
            not isinstance(question, str)
            or question not in manual_text
            or not isinstance(answer, str)
            or answer not in manual_text
        ):
            mismatches.add(f"coverage_principles:{index}")
    return ContentDiff(mismatches=frozenset(mismatches))


def audit_facts(
    opdir: Path | str,
    facts_path: Path | str,
    *,
    manual: Path | str | None = None,
    publication: str,
) -> FactsAudit:
    facts, issue_set = _validate_facts(
        opdir,
        facts_path,
        publication=publication,
    )
    facts_sync = not issue_set
    content_sync: bool | None = None
    content_mismatches: frozenset[str] = frozenset()
    if manual is not None:
        try:
            content = compare_manual_content(opdir, facts_path, manual)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            issue_set.add("manual-content")
            content_sync = False
        else:
            content_mismatches = content.mismatches
            content_sync = not content_mismatches
            if content_mismatches:
                issue_set.add("content")
        if publication == "final":
            manual_text = Path(manual).read_text(encoding="utf-8")
            if any(placeholder in manual_text for placeholder in FINAL_PLACEHOLDERS):
                issue_set.add("final-placeholder")
                content_sync = False

    publishable = bool(
        facts_sync
        and (content_sync is not False)
        and publication == "final"
        and facts.get("provenance") == "production"
        and facts.get("production_eligible") is True
    )
    return FactsAudit(
        facts_sync=facts_sync,
        content_sync=content_sync,
        publishable=publishable,
        issues=frozenset(issue_set),
        content_mismatches=content_mismatches,
    )


def parse_capability_checklist(path: Path | str) -> ChecklistState:
    checklist = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(checklist, dict):
        raise ValueError("capability checklist must be a JSON object")
    operator = checklist.get("op")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("capability checklist op must be a non-empty string")
    framework_scope = checklist.get("framework_scope")
    if (
        not isinstance(framework_scope, list)
        or not framework_scope
        or any(
            not isinstance(framework, str) or not framework.strip()
            for framework in framework_scope
        )
    ):
        raise ValueError("framework_scope must be a non-empty string list")
    frameworks = [framework.strip().lower() for framework in framework_scope]
    if len(frameworks) != len(set(frameworks)):
        raise ValueError("framework_scope contains duplicate entries")

    capabilities = checklist.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError("capabilities must be a non-empty list")

    case_ids: set[str] = set()
    capability_ids: set[str] = set()
    current_schema = True
    for capability in capabilities:
        if not isinstance(capability, dict):
            raise ValueError("each capability must be a JSON object")
        capability_id = capability.get("id")
        if (
            not isinstance(capability_id, str)
            or not capability_id.strip()
            or capability_id in capability_ids
        ):
            current_schema = False
        elif isinstance(capability_id, str):
            capability_ids.add(capability_id)
        if (
            not isinstance(capability.get("desc"), str)
            or not capability.get("desc", "").strip()
        ):
            current_schema = False
        if "covered_by" not in capability:
            current_schema = False
        covered_by = capability.get("covered_by", [])
        if not isinstance(covered_by, list):
            raise ValueError("capability covered_by must be a list")
        if not covered_by:
            current_schema = False
        case_ids.update(_normalize_case_id(case_id) for case_id in covered_by)
        if not isinstance(capability.get("match"), dict):
            current_schema = False
    return ChecklistState(
        operator=operator.strip(),
        frameworks=frozenset(frameworks),
        capability_count=len(capabilities),
        covered_case_ids=frozenset(case_ids),
        current_schema=current_schema,
    )


def parse_capability_case_ids(path: Path | str) -> frozenset[str]:
    return parse_capability_checklist(path).covered_case_ids


def compare_manual_cases(opdir: Path | str, manual: Path | str) -> CaseDiff:
    _, sources = _resolve_core_sources(opdir)
    expected = parse_op_spec_case_ids(sources[Path("scripts/op_spec.py")])
    capability_cases = parse_capability_case_ids(
        sources[Path("scripts/capability_checklist.json")]
    )
    actual_sequence = parse_manual_case_id_sequence(manual)
    actual = frozenset(actual_sequence)
    duplicates = frozenset(
        case_id
        for case_id, count in Counter(actual_sequence).items()
        if count != 1
    )
    return CaseDiff(
        missing=(expected | capability_cases) - actual,
        extra=actual - expected,
        duplicates=duplicates,
    )


def _summary_state(summary_path: Path) -> SummaryState:
    try:
        text = summary_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return SummaryState(
            failing=False,
            trustworthy_success=False,
            operator=None,
            capability_covered=None,
            capability_total=None,
        )

    lines = text.splitlines()
    verdict_index = next(
        (
            index
            for index in range(len(lines) - 1, -1, -1)
            if lines[index].lstrip().startswith("VERDICT:")
        ),
        None,
    )
    verdict = None
    harness_exit = None
    if verdict_index is not None:
        next_index = verdict_index + 1
        while next_index < len(lines) and not lines[next_index].strip():
            next_index += 1
        if next_index < len(lines):
            exit_match = HARNESS_EXIT.fullmatch(lines[next_index])
            if exit_match:
                verdict = lines[verdict_index].strip()
                harness_exit = int(exit_match.group(1))

    fail_counts = [int(count) for count in FAIL_COUNT.findall(verdict or "")]
    err_counts = [int(count) for count in ERR_COUNT.findall(verdict or "")]
    capability = CAPABILITY_COUNT.search(verdict or "")
    operator_match = VERDICT_OP.search(verdict or "")
    capability_covered = int(capability.group(1)) if capability else None
    capability_total = int(capability.group(2)) if capability else None
    capabilities_full = bool(
        capability
        and capability_covered == capability_total
        and capability_total is not None
        and capability_total > 0
    )
    failing = (
        (harness_exit is not None and harness_exit != 0)
        or any(count != 0 for count in fail_counts)
        or any(count != 0 for count in err_counts)
        or bool(
            capability
            and capability_covered is not None
            and capability_total is not None
            and capability_covered != capability_total
        )
    )
    trustworthy_success = bool(
        verdict
        and harness_exit == 0
        and fail_counts
        and all(count == 0 for count in fail_counts)
        and all(count == 0 for count in err_counts)
        and capabilities_full
    )
    return SummaryState(
        failing=failing,
        trustworthy_success=trustworthy_success,
        operator=operator_match.group(1) if operator_match else None,
        capability_covered=capability_covered,
        capability_total=capability_total,
    )


def _contains_identifier(text: str, identifier: str) -> bool:
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(identifier)}(?![A-Za-z0-9_])",
            text,
            re.IGNORECASE,
        )
    )


def _markdown_headings(text: str) -> frozenset[str]:
    return frozenset(
        match.group(1).strip().casefold()
        for match in MARKDOWN_HEADING.finditer(text)
    )


def classify_opdir(opdir: Path | str) -> str:
    try:
        opdir_path, sources = _resolve_core_sources(opdir)
        core_text = {
            relative: sources[relative].read_text(encoding="utf-8")
            for relative in CORE_SOURCES
        }
        if any(not text.strip() for text in core_text.values()):
            return "D"
        op_spec = parse_op_spec(sources[Path("scripts/op_spec.py")])
        checklist = parse_capability_checklist(
            sources[Path("scripts/capability_checklist.json")]
        )
    except (OSError, UnicodeError, json.JSONDecodeError, SyntaxError, ValueError):
        return "D"

    expected_cases = frozenset(op_spec.case_ids)
    if (
        op_spec.operator != checklist.operator
        or op_spec.frameworks != checklist.frameworks
        or not checklist.covered_case_ids.issubset(expected_cases)
    ):
        return "D"

    spec_text = core_text[Path("docs/spec.md")]
    contract_text = core_text[Path("docs/implementation-contract.md")]
    identity_tokens = (
        checklist.operator,
        *sorted(checklist.frameworks),
    )
    contract_headings = _markdown_headings(contract_text)
    current_schema = (
        checklist.current_schema
        and all(
            _contains_identifier(spec_text, token)
            for token in identity_tokens
        )
        and all(
            _contains_identifier(contract_text, token)
            for token in identity_tokens
        )
        and all(key.casefold() in contract_headings for key in CONTRACT_KEYS)
    )
    summary = _summary_state(opdir_path / "verify_summary.txt")
    summary_matches = (
        summary.operator == checklist.operator
        and summary.capability_total == checklist.capability_count
    )
    if summary.operator == checklist.operator and summary.failing:
        return "C"
    if current_schema and summary_matches and summary.trustworthy_success:
        return "A"
    return "B"


def _format_case_ids(case_ids: frozenset[str]) -> str:
    return ",".join(sorted(case_ids)) if case_ids else "NONE"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit operator-manual inputs, canonical facts, and rendered content."
        )
    )
    parser.add_argument("--opdir", required=True, type=Path)
    parser.add_argument("--facts", type=Path)
    parser.add_argument("--manual", type=Path)
    parser.add_argument(
        "--publication",
        choices=("draft", "migration-draft", "final"),
        default="draft",
    )
    args = parser.parse_args(argv)

    tier = classify_opdir(args.opdir)
    print(f"OP_MANUAL_INPUT_TIER={tier}")

    sync_failed = False
    if args.facts is None:
        print("OP_MANUAL_FACTS_SYNC=SKIP")
        print("OP_MANUAL_CONTENT_SYNC=SKIP")
        print("OP_MANUAL_CONTENT_MISMATCH=NONE")
    else:
        try:
            facts_audit = audit_facts(
                args.opdir,
                args.facts,
                manual=args.manual,
                publication=args.publication,
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            SyntaxError,
            ValueError,
        ):
            sync_failed = True
            print("OP_MANUAL_FACTS_SYNC=FAIL")
            print("OP_MANUAL_CONTENT_SYNC=FAIL")
            print("OP_MANUAL_CONTENT_MISMATCH=UNKNOWN")
        else:
            if not facts_audit.facts_sync:
                sync_failed = True
            if facts_audit.content_sync is False:
                sync_failed = True
            print(
                "OP_MANUAL_FACTS_SYNC="
                f"{'PASS' if facts_audit.facts_sync else 'FAIL'}"
            )
            content_status = (
                "SKIP"
                if facts_audit.content_sync is None
                else "PASS"
                if facts_audit.content_sync
                else "FAIL"
            )
            print(f"OP_MANUAL_CONTENT_SYNC={content_status}")
            print(
                "OP_MANUAL_CONTENT_MISMATCH="
                + (
                    ",".join(sorted(facts_audit.content_mismatches))
                    if facts_audit.content_mismatches
                    else "NONE"
                )
            )
            if facts_audit.issues:
                print(
                    "OP_MANUAL_FACTS_ISSUES="
                    + ",".join(sorted(facts_audit.issues))
                )

    if args.manual is None:
        print("OP_MANUAL_CASE_SYNC=SKIP")
    else:
        try:
            diff = compare_manual_cases(args.opdir, args.manual)
        except (OSError, UnicodeError, SyntaxError, ValueError):
            sync_failed = True
            print("OP_MANUAL_CASE_SYNC=FAIL")
            print("OP_MANUAL_CASE_MISSING=UNKNOWN")
            print("OP_MANUAL_CASE_EXTRA=UNKNOWN")
            print("OP_MANUAL_CASE_DUPLICATE=UNKNOWN")
        else:
            case_failed = bool(diff.missing or diff.extra or diff.duplicates)
            sync_failed = sync_failed or case_failed
            print(f"OP_MANUAL_CASE_SYNC={'FAIL' if case_failed else 'PASS'}")
            print(f"OP_MANUAL_CASE_MISSING={_format_case_ids(diff.missing)}")
            print(f"OP_MANUAL_CASE_EXTRA={_format_case_ids(diff.extra)}")
            print(
                f"OP_MANUAL_CASE_DUPLICATE={_format_case_ids(diff.duplicates)}"
            )

    return 1 if tier == "D" or sync_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
