#!/usr/bin/env python3
"""Regression tests for the document-first pre-source artifact gate."""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


GATE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gate_artifacts.py"
SPEC = importlib.util.spec_from_file_location("operator_artifact_gate", GATE_PATH)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_initial_manual_fixture(tmp_path: Path, *, mode="integrated-initial") -> Path:
    opdir = tmp_path / "op"
    docs = opdir / "docs"
    scripts = opdir / "scripts"
    docs.mkdir(parents=True)
    scripts.mkdir()
    sources = {
        "spec": docs / "spec.md",
        "implementation_contract": docs / "implementation-contract.md",
        "capability_checklist": scripts / "capability_checklist.json",
        "op_spec": scripts / "op_spec.py",
    }
    for name, path in sources.items():
        path.write_text(f"ReduceSumSquare {name}\n", encoding="utf-8")
    facts = {
        "schema_version": 1,
        "mode": mode,
        "operator": "ReduceSumSquare",
        "production_eligible": False,
        "sources": {
            name: {
                "path": path.relative_to(opdir).as_posix(),
                "sha256": sha256(path),
            }
            for name, path in sources.items()
        },
    }
    (docs / "operator-manual-facts.json").write_text(
        json.dumps(facts, indent=2) + "\n", encoding="utf-8"
    )
    (docs / "reducesumsquare-operator-design-doc.md").write_text(
        "# ReduceSumSquare 算子设计文档\n", encoding="utf-8"
    )
    (docs / "reducesumsquare-operator-verify-doc.md").write_text(
        "# ReduceSumSquare 算子验证文档\n", encoding="utf-8"
    )
    return opdir


def install_manual_audit(tmp_path: Path, *, passed=True) -> Path:
    script = tmp_path / "separate plugin location" / "manual resources" / "audit_manual_inputs.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    if passed:
        output = (
            "OP_MANUAL_FACTS_SYNC=PASS\n"
            "OP_MANUAL_CONTENT_SYNC=PASS\n"
            "OP_MANUAL_CASE_SYNC=PASS\n"
        )
        exit_code = 0
    else:
        output = (
            "OP_MANUAL_FACTS_SYNC=PASS\n"
            "OP_MANUAL_CONTENT_SYNC=FAIL\n"
            "OP_MANUAL_CASE_SYNC=PASS\n"
        )
        exit_code = 1
    script.write_text(
        "import sys\n"
        f"sys.stdout.write({output!r})\n"
        f"raise SystemExit({exit_code})\n",
        encoding="utf-8",
    )
    return script.resolve()


def test_initial_manual_gate_accepts_current_prepare_sources(tmp_path):
    script = install_manual_audit(tmp_path)
    opdir = make_initial_manual_fixture(tmp_path)
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors, script)
    assert errors == []


def test_initial_manual_gate_rejects_missing_draft(tmp_path):
    script = install_manual_audit(tmp_path)
    opdir = make_initial_manual_fixture(tmp_path)
    (opdir / "docs/reducesumsquare-operator-design-doc.md").unlink()
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors, script)
    assert any("reducesumsquare-operator-design-doc.md" in error for error in errors)


def test_initial_manual_gate_rejects_missing_verify_document(tmp_path):
    script = install_manual_audit(tmp_path)
    opdir = make_initial_manual_fixture(tmp_path)
    (opdir / "docs/reducesumsquare-operator-verify-doc.md").unlink()
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors, script)
    assert any("reducesumsquare-operator-verify-doc.md" in error for error in errors)


def test_initial_manual_gate_rejects_source_changed_after_draft(tmp_path):
    script = install_manual_audit(tmp_path)
    opdir = make_initial_manual_fixture(tmp_path)
    (opdir / "docs/implementation-contract.md").write_text(
        "ReduceSumSquare changed after initial manual\n", encoding="utf-8"
    )
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors, script)
    assert any("implementation_contract.sha256" in error for error in errors)


def test_initial_manual_gate_rejects_final_facts_before_source(tmp_path):
    script = install_manual_audit(tmp_path)
    opdir = make_initial_manual_fixture(tmp_path, mode="integrated-final")
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors, script)
    assert any("mode must be integrated-initial" in error for error in errors)


def test_initial_manual_gate_rejects_failed_content_audit(tmp_path):
    script = install_manual_audit(tmp_path, passed=False)
    opdir = make_initial_manual_fixture(tmp_path)
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors, script)
    assert any("integrated-initial manual audit failed" in error for error in errors)


@pytest.mark.parametrize("invalid", ["missing-argument", "missing-file", "relative-path"])
def test_initial_manual_gate_rejects_unresolved_audit_script(tmp_path, invalid):
    opdir = make_initial_manual_fixture(tmp_path)
    script = {
        "missing-argument": None,
        "missing-file": tmp_path / "not installed" / "audit_manual_inputs.py",
        "relative-path": Path("hs-design-op-manual/scripts/audit_manual_inputs.py"),
    }[invalid]
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors, script)
    assert len(errors) == 1
    expected = {
        "missing-argument": "--manual-audit-script is required",
        "missing-file": "missing manual audit script",
        "relative-path": "must be an absolute path",
    }[invalid]
    assert expected in errors[0]


@pytest.mark.parametrize("missing_token", ["FACTS", "CONTENT", "CASE"])
def test_manual_audit_requires_all_pass_markers_even_with_zero_exit(tmp_path, missing_token):
    script = install_manual_audit(tmp_path)
    script.write_text(
        script.read_text(encoding="utf-8").replace(
            f"OP_MANUAL_{missing_token}_SYNC=PASS", f"OP_MANUAL_{missing_token}_SYNC=FAIL"
        ),
        encoding="utf-8",
    )
    errors = []
    gate.check_initial_manual(make_initial_manual_fixture(tmp_path), "ReduceSumSquare", errors, script)
    assert any("integrated-initial manual audit failed (exit=0" in error for error in errors)


def test_manual_audit_rejects_nonzero_exit_with_all_pass_markers(tmp_path):
    script = install_manual_audit(tmp_path)
    script.write_text(
        script.read_text(encoding="utf-8").replace("SystemExit(0)", "SystemExit(1)"),
        encoding="utf-8",
    )
    errors = []
    gate.check_initial_manual(make_initial_manual_fixture(tmp_path), "ReduceSumSquare", errors, script)
    assert any("integrated-initial manual audit failed (exit=1" in error for error in errors)


def test_manual_audit_works_after_independent_installation_with_spaces(tmp_path):
    installed_gate = tmp_path / "operator plugin" / "nested install" / "scripts" / "gate_artifacts.py"
    installed_gate.parent.mkdir(parents=True)
    shutil.copy2(GATE_PATH, installed_gate)
    spec = importlib.util.spec_from_file_location("independently_installed_gate", installed_gate)
    installed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installed)
    script = install_manual_audit(tmp_path)
    opdir = make_initial_manual_fixture(tmp_path)
    errors = []
    installed.check_initial_manual(opdir, "ReduceSumSquare", errors, script)
    assert errors == []


@pytest.mark.parametrize(
    ("stage", "source_only", "audits"),
    [
        ("step3", False, False),
        ("prepare", False, False),
        ("pre-source", True, False),
        ("pre-code", True, False),
        ("pre-source", False, True),
        ("pre-code", False, True),
        ("pre-verify", False, True),
    ],
)
def test_cli_requires_resolved_audit_only_for_document_stages(tmp_path, monkeypatch, capsys, stage, source_only, audits):
    opdir = make_initial_manual_fixture(tmp_path)
    for name in ("decision.md", "link-analysis.md"):
        (opdir / "docs" / name).write_text("ReduceSumSquare planning stub\n", encoding="utf-8")
    # Scope this test to audit dispatch. Other source/checklist/review gates have
    # their own regression cases and are deliberately stubbed here.
    for name in (
        "require_mentions", "load_checklist", "check_source_freeze",
        "check_existing_capability_review", "check_contract", "check_op_spec_text", "check_code_review",
    ):
        monkeypatch.setattr(gate, name, lambda *args: None)
    argv = [
        str(GATE_PATH), "--opdir", str(opdir), "--op", "ReduceSumSquare",
        "--stage", stage, "--code-root", str(tmp_path), "--plan-run-id", "plan-001",
    ]
    if source_only:
        argv.append("--source-only")
    monkeypatch.setattr(sys, "argv", argv)
    assert gate.main() == (1 if audits else 0)
    output = capsys.readouterr().out
    assert ("--manual-audit-script is required" in output) == audits
    if audits:
        script = install_manual_audit(tmp_path)
        monkeypatch.setattr(sys, "argv", argv + ["--manual-audit-script", str(script)])
        assert gate.main() == 0


def test_source_freeze_detects_source_change_without_requiring_clean_tree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    source = repo / "kernel.cc"
    source.write_text("int value = 1;\n", encoding="utf-8")
    subprocess.run(["git", "add", "kernel.cc"], cwd=repo, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=Skill Test", "-c", "user.email=skill@test.invalid",
            "commit", "-q", "-m", "baseline",
        ],
        cwd=repo,
        check=True,
    )
    # A pre-existing dirty file is part of the accepted baseline.
    source.write_text("int value = 2;\n", encoding="utf-8")
    opdir = tmp_path / "op"
    gate.write_source_freeze(
        opdir, repo, "ReduceSumSquare", ["onnx"], "plan-001"
    )
    errors = []
    gate.check_source_freeze(
        opdir, repo, "ReduceSumSquare", ["onnx"], "plan-001", errors
    )
    assert errors == []

    source.write_text("int value = 3;\n", encoding="utf-8")
    gate.check_source_freeze(
        opdir, repo, "ReduceSumSquare", ["onnx"], "plan-001", errors
    )
    assert any("source fingerprint changed" in error for error in errors)


def test_source_freeze_cannot_be_silently_overwritten_and_rotation_is_archived(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    source = repo / "kernel.cc"
    source.write_text("int value = 1;\n", encoding="utf-8")
    subprocess.run(["git", "add", "kernel.cc"], cwd=repo, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=Skill Test", "-c", "user.email=skill@test.invalid",
            "commit", "-q", "-m", "baseline",
        ],
        cwd=repo,
        check=True,
    )
    opdir = tmp_path / "op"
    gate.write_source_freeze(opdir, repo, "BitShift", ["onnx"], "plan-001")
    try:
        gate.write_source_freeze(opdir, repo, "BitShift", ["onnx"], "plan-001")
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("same plan run unexpectedly overwrote source-freeze")

    gate.write_source_freeze(
        opdir,
        repo,
        "BitShift",
        ["onnx"],
        "plan-002",
        rotate_existing=True,
    )
    archives = list((opdir / "docs/source-freeze-history").glob("plan-001-*.json"))
    assert len(archives) == 1


def test_source_freeze_hashes_all_untracked_regular_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    tracked = repo / "README.md"
    tracked.write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=Skill Test", "-c", "user.email=skill@test.invalid",
            "commit", "-q", "-m", "baseline",
        ],
        cwd=repo,
        check=True,
    )
    include = repo / "kernel.inc"
    include.write_text("VALUE=1\n", encoding="utf-8")
    opdir = tmp_path / "op"
    gate.write_source_freeze(opdir, repo, "BitShift", ["onnx"], "plan-001")
    include.write_text("VALUE=2\n", encoding="utf-8")
    errors = []
    gate.check_source_freeze(
        opdir, repo, "BitShift", ["onnx"], "plan-001", errors
    )
    assert any("source fingerprint changed" in error for error in errors)


def test_source_freeze_is_bound_to_plan_operator_and_framework(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    tracked = repo / "kernel.cc"
    tracked.write_text("int value = 1;\n", encoding="utf-8")
    subprocess.run(["git", "add", "kernel.cc"], cwd=repo, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=Skill Test", "-c", "user.email=skill@test.invalid",
            "commit", "-q", "-m", "baseline",
        ],
        cwd=repo,
        check=True,
    )
    opdir = tmp_path / "op"
    gate.write_source_freeze(
        opdir, repo, "BitShift", ["onnx", "tflite"], "plan-001"
    )
    errors = []
    gate.check_source_freeze(opdir, repo, "Other", ["caffe"], "plan-999", errors)
    assert any("plan_run_id" in error for error in errors)
    assert any("operator" in error for error in errors)
    assert any("framework_scope" in error for error in errors)


def test_source_only_flag_is_restricted_to_source_gates(tmp_path):
    opdir = tmp_path / "op"
    opdir.mkdir()
    result = subprocess.run(
        [
            "python",
            str(GATE_PATH),
            "--opdir",
            str(opdir),
            "--op",
            "BitShift",
            "--stage",
            "prepare",
            "--source-only",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "--source-only is only valid with stage=pre-source or stage=pre-code" in result.stdout
