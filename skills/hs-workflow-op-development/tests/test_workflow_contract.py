#!/usr/bin/env python3
"""Static contract checks for the operator workflow and its stage-specific skills."""

from pathlib import Path
import re


SKILLS_ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    return (SKILLS_ROOT / relative).read_text(encoding="utf-8")


def test_board_sdk_location_requires_explicit_user_input():
    workflow = read("hs-workflow-op-development/SKILL.md")
    board = read("hs-verify-op-board/SKILL.md")
    for text in (workflow, board):
        assert "FIRMWARE_SDK_ROOT" in text
        assert "用户" in text
        assert re.search(r"(没有时必须向用户询问|没有路径时暂停板端阶段并询问)", text)
        assert re.search(r"禁止通过搜索磁盘|不能替用户选择", text)


def test_board_workflow_keeps_all_required_gates():
    workflow = read("hs-workflow-op-development/SKILL.md")
    board = read("hs-verify-op-board/SKILL.md")
    integration = read("hs-verify-op-board/chips/ws63/references/sdk-integration.md")
    combined = "\n".join((workflow, board, integration))
    required = (
        "build_micro.py",
        "libmicro_runtime.a",
        "libnet.a",
        "prepare_sample.py",
        "integrate_sdk.py",
        "verify_wiring.py",
        "BOARD_WIRING_GATE=PASS",
        "fbb build",
        "verify_firmware.py",
        "FIRMWARE_CONTENT_GATE=PASS",
        "fbb flash",
        "--json-summary",
        "DEVICE_NOT_RESPONDING",
        "--manual-reset",
        "board_accuracy.py",
        "ACCURACY_VERDICT=PASS",
    )
    for token in required:
        assert token in combined, token


def test_board_accuracy_requires_complete_same_run_tensor_evidence():
    board = read("hs-verify-op-board/SKILL.md")
    for token in (
        "同一 case",
        "完整输出Tensor",
        "Tensor 数量",
        "shape",
        "元素数",
        "余弦",
        "早于本轮烧录",
    ):
        assert token in board, token


def test_active_skills_do_not_expose_internal_version_comparisons():
    active = (
        "hs-workflow-op-development/SKILL.md",
        "hs-dev-op-implement/SKILL.md",
        "hs-verify-op-host/SKILL.md",
        "hs-verify-op-board/SKILL.md",
        "hs-design-op-manual/SKILL.md",
        "hs-workflow-mslite-env-setup/SKILL.md",
    )
    forbidden = ("旧流程", "新版", "旧版", "skill-backups", "legacy migration")
    for relative in active:
        text = read(relative)
        for phrase in forbidden:
            assert phrase not in text, f"{relative}: {phrase}"


def test_environment_preparation_is_intent_and_sdk_path_gated():
    workflow = read("hs-workflow-op-development/SKILL.md")
    for token in (
        "环境准备分流",
        "只想安装或检查 `fbb CLI`",
        "已明确提供 SDK 源码路径",
        "没有 SDK，且明确要求编译/上板",
        "只做算子源码、MindSpore Lite 构建或 Host 验证",
        "禁止下载另一份 SDK",
        "不得把 `fbb sdk install <chip>` 当作默认补救动作",
    ):
        assert token in workflow, token


def test_environment_skill_missing_is_reported_before_board_stage():
    workflow = read("hs-workflow-op-development/SKILL.md")
    for token in (
        "环境准备 Skill 的可用性门禁",
        "该使用者当前会话",
        "ENV_PREP_SKILL=NOT_REQUIRED",
        "ENV_PREP_SKILL=UNAVAILABLE",
        "BOARD_STAGE=BLOCKED",
        "不得启动后台 `fbb build`/`fbb flash`",
        "期望文件：<skill-root>/hs-dev-env-prep/SKILL.md",
    ):
        assert token in workflow, token


def test_environment_build_flash_skills_share_install_source():
    workflow = read("hs-workflow-op-development/SKILL.md")
    source = "https://gitcode.com/HiSpark/hibot-skills/tree/master/skills"
    assert workflow.count(source) >= 2
    for skill in ("hs-dev-env-prep", "hs-dev-build", "hs-dev-flash"):
        assert f"<skill-root>/{skill}/SKILL.md" in workflow
    assert "references/" in workflow
    assert "scripts/" in workflow


def test_workflow_route_disambiguation_prefers_full_flow_for_generic_requests():
    workflow = read("hs-workflow-op-development/SKILL.md")
    for token in (
        "实现/适配/新增 MatMul 算子",
        "在 WS63 上实现/运行 X 算子",
        "只改 MindSpore Lite 源码，不测试、不编译、不写文档",
        "只用 hs-dev-op-implement 分析/补 X",
        "不得降级为 `hs-dev-op-implement`",
        "先按完整 workflow",
    ):
        assert token in workflow, token


def test_workflow_requires_document_first_and_terminal_background_reporting():
    workflow = read("hs-workflow-op-development/SKILL.md")
    assert workflow.index("stage1：文档事实和实现合同先行") < workflow.index("stage2：实现源码")
    for token in ("RUN_ID", "首个真实错误", "终态通知", "不能关闭承载任务的窗口"):
        assert token in workflow, token


def test_implement_requires_post_code_review_and_fold_checks():
    impl = read("hs-dev-op-implement/SKILL.md")
    quality = read("hs-dev-op-implement/references/code-quality-gate.md")
    gate = read("hs-dev-op-implement/scripts/gate_artifacts.py")
    for text in (impl, quality, gate):
        assert "code-review.md" in text
        assert "folding_and_rewrite_cases" in text or "折叠" in text
        assert "registration_matrix" in text or "注册键" in text
    assert "check_code_review" in gate


def test_leaf_trigger_is_explicit_and_board_stage_numbers_match():
    impl = read("hs-dev-op-implement/SKILL.md")
    board = read("hs-verify-op-board/SKILL.md")
    workflow = read("hs-workflow-op-development/SKILL.md")
    assert "explicitly requests source-only work" in impl
    assert "顶层stage6共同持有" in board
    assert "workflow stage6 的 sample/adaptor/固件接线" in board
    assert "stage6 可选" in workflow and "stage7 可选" in workflow


def test_structured_review_and_folding_gates_are_mechanical():
    gate = read("hs-dev-op-implement/scripts/gate_artifacts.py")
    checklist = read("hs-verify-op-host/scripts/capability_checklist.template.json")
    assert "machine-readable JSON review object" in gate
    assert "REVIEW_LIST_RULES" in gate
    assert "folding_and_rewrite" in gate
    assert "blocked" in checklist and "allowed" in checklist


def test_host_run_identity_is_carried_by_entry_and_waiter():
    host = read("hs-verify-op-host/SKILL.md")
    runner = read("hs-verify-op-host/scripts/run_all_cases.py")
    waiter = read("hs-verify-op-host/scripts/wait_verify.sh")
    assert "--run-id" in host and "RUN_ID" in runner
    assert "RUN_ID_MISMATCH" in waiter
