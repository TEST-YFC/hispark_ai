#!/usr/bin/env python3
"""Regression tests for the document-first pre-source artifact gate."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path


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


def install_manual_audit(monkeypatch, tmp_path: Path, *, passed=True) -> None:
    script = tmp_path / "manual_audit.py"
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
    monkeypatch.setattr(gate, "MANUAL_AUDIT_SCRIPT", script)


def test_initial_manual_gate_accepts_current_prepare_sources(tmp_path, monkeypatch):
    install_manual_audit(monkeypatch, tmp_path)
    opdir = make_initial_manual_fixture(tmp_path)
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors)
    assert errors == []


def test_initial_manual_gate_rejects_missing_draft(tmp_path, monkeypatch):
    install_manual_audit(monkeypatch, tmp_path)
    opdir = make_initial_manual_fixture(tmp_path)
    (opdir / "docs/reducesumsquare-operator-design-doc.md").unlink()
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors)
    assert any("reducesumsquare-operator-design-doc.md" in error for error in errors)


def test_initial_manual_gate_rejects_missing_verify_document(tmp_path, monkeypatch):
    install_manual_audit(monkeypatch, tmp_path)
    opdir = make_initial_manual_fixture(tmp_path)
    (opdir / "docs/reducesumsquare-operator-verify-doc.md").unlink()
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors)
    assert any("reducesumsquare-operator-verify-doc.md" in error for error in errors)


def test_initial_manual_gate_rejects_source_changed_after_draft(tmp_path, monkeypatch):
    install_manual_audit(monkeypatch, tmp_path)
    opdir = make_initial_manual_fixture(tmp_path)
    (opdir / "docs/implementation-contract.md").write_text(
        "ReduceSumSquare changed after initial manual\n", encoding="utf-8"
    )
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors)
    assert any("implementation_contract.sha256" in error for error in errors)


def test_initial_manual_gate_rejects_final_facts_before_source(tmp_path, monkeypatch):
    install_manual_audit(monkeypatch, tmp_path)
    opdir = make_initial_manual_fixture(tmp_path, mode="integrated-final")
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors)
    assert any("mode must be integrated-initial" in error for error in errors)


def test_initial_manual_gate_rejects_failed_content_audit(tmp_path, monkeypatch):
    install_manual_audit(monkeypatch, tmp_path, passed=False)
    opdir = make_initial_manual_fixture(tmp_path)
    errors = []
    gate.check_initial_manual(opdir, "ReduceSumSquare", errors)
    assert any("integrated-initial manual audit failed" in error for error in errors)


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
