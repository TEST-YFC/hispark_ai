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
        assert re.search(r"禁止通过搜索磁盘|不能替用户选择", text)
    assert "没有时必须向用户询问并停在Stage0" in workflow
    assert "不能通过\n`EXECUTION_CONFIRM_GATE`或进入stage1" in workflow
    assert "只有用户明确切换为`BOARD_POLICY=HOST_ONLY`时" in workflow
    assert re.search(r"没有路径时暂停板端阶段并询问", board)


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
    stage1 = workflow.split("## stage1：", 1)[1].split("## stage2：", 1)[0]
    stage2 = workflow.split("## stage2：", 1)[1].split("## stage3：", 1)[0]
    assert stage1.index("hs-dev-op-implement mode=prepare") < stage1.index(
        "hs-design-op-manual mode=integrated-initial"
    )
    assert stage1.index("hs-design-op-manual mode=integrated-initial") < stage1.index(
        "gate_artifacts.py --stage pre-source"
    )
    assert "PRE_SOURCE_GATE=PASS" in stage1
    assert "hs-dev-op-implement mode=apply" in stage2
    assert "不能先改代码再更新草稿" in stage1
    for token in ("RUN_ID", "首个真实错误", "终态通知", "不能关闭承载任务的窗口"):
        assert token in workflow, token


def test_document_first_roles_and_mechanical_gate_do_not_conflict():
    impl = read("hs-dev-op-implement/SKILL.md")
    manual = read("hs-design-op-manual/SKILL.md")
    gate = read("hs-dev-op-implement/scripts/gate_artifacts.py")
    for token in (
        "mode=prepare",
        "mode=apply",
        "OP_PLAN_GATE=PASS",
        "PRE_SOURCE_GATE=PASS",
        "本skill不得自行调用文档Skill",
    ):
        assert token in impl, token
    assert "只能在父流程已经完成`hs-dev-op-implement mode=prepare`" in manual
    assert "check_initial_manual" in gate
    assert '"pre-source"' in gate
    assert "operator-manual-facts.json" in gate
    assert "-operator-design-doc.md" in gate
    assert "-operator-verify-doc.md" in gate
    assert "sources.{name}.sha256 does not match current file" in gate
    assert '"source-freeze"' in gate
    assert "source fingerprint changed after source-freeze" in gate
    assert "plan_run_id does not match current --plan-run-id" in gate
    assert "cannot overwrite source freeze with the same plan run ID" in gate
    assert '"untracked_files"' in gate
    assert "OP_MANUAL_FACTS_SYNC=PASS" in gate
    assert "OP_MANUAL_CONTENT_SYNC=PASS" in gate
    assert "OP_MANUAL_CASE_SYNC=PASS" in gate


def test_frozen_contract_and_planned_cases_cannot_change_during_apply_or_host():
    workflow = read("hs-workflow-op-development/SKILL.md")
    host = read("hs-verify-op-host/SKILL.md")
    apply_stage = workflow.split("## stage2：", 1)[1].split("## stage3：", 1)[0]
    host_stage = workflow.split("## stage4：", 1)[1].split("## stage5：", 1)[0]
    assert "不得在apply中直接\n修改冻结合同" in apply_stage
    assert "返回stage1" in apply_stage
    assert "读取并执行stage1冻结的完整`op_spec.py`" in host_stage
    assert "不把Host阶段当成正常改写计划用例的阶段" in host_stage
    assert "完整workflow的Host阶段不得直接新增、删除或改写case" in host


def test_final_manual_is_host_gated_and_board_report_is_signed_separately():
    manual = read("hs-design-op-manual/SKILL.md")
    assert "验证文档" in manual
    assert "不能把固件构建写成板测通过" in manual


def test_design_and_verify_templates_match_manual_audit_contract():
    design = read("hs-design-op-manual/references/operator-design-doc-template.md")
    verify = read("hs-design-op-manual/references/operator-verify-doc-template.md")
    assert "## 3. MindSpore Lite Micro 软件设计" in design
    assert "## 1. 测试设计" in verify
    assert "## 2. 运行验证结果" in verify
    assert "## 3. 证据索引" in verify
    expected_headers = (
        "用例编号",
        "框架/source entry",
        "模型 dtype",
        "已覆盖运行通路",
        "input_shape",
        "输入数据特征（value_domain）",
        "算子属性",
        "预期输出",
    )
    table_line = next(line for line in verify.splitlines() if line.startswith("| 用例编号"))
    assert all(header in table_line for header in expected_headers)
    assert "{op}-operator-design-doc.md" in design
    assert "{op}-operator-verify-doc.md" in verify
    assert "七类能力不是每次推理按顺序执行" in design


def test_operator_documents_have_one_owner_directory_and_fixed_pair():
    manual = read("hs-design-op-manual/SKILL.md")
    workflow = read("hs-workflow-op-development/SKILL.md")
    audit = read("hs-design-op-manual/scripts/audit_manual_inputs.py")
    design_template = read(
        "hs-design-op-manual/references/operator-design-doc-template.md"
    )
    verify_template = read(
        "hs-design-op-manual/references/operator-verify-doc-template.md"
    )
    for name in (
        "<opdir>/docs/{op}-operator-design-doc.md",
        "<opdir>/docs/{op}-operator-verify-doc.md",
    ):
        assert name in manual
        assert name in workflow
    standalone = manual.split("### 独立模式", 1)[1].split("### 产物集成模式", 1)[0]
    assert "<opdir>/docs/" in standalone
    assert "成对生成" in manual
    output_table = manual.split("## 输出决策", 1)[1].split("## 自检与最终复核", 1)[0]
    assert "<code_root>/" not in output_table
    document_kinds = set(
        re.findall(r"\{op\}-operator-(design|verify)-doc\.md", manual)
    )
    assert document_kinds == {"design", "verify"}
    audit_arguments = set(
        re.findall(r'parser\.add_argument\(\s*"([^"]+)"', audit)
    )
    assert audit_arguments == {
        "--opdir",
        "--facts",
        "--design",
        "--verify",
        "--publication",
    }
    assert "4(?:[-.]2)" not in audit
    for template in (design_template, verify_template):
        numbered_chapters = re.findall(r"^##\s+\d+\.\s+", template, re.MULTILINE)
        assert len(numbered_chapters) == 3
    for integration_only_artifact in (
        "operator-manual-facts.json",
        "scripts/op_spec.py",
        "verify_summary.txt",
    ):
        assert integration_only_artifact not in verify_template
    assert "只列本次模式下真实存在" in verify_template
    assert "带备份回滚的成对发布" in manual
    assert "不得声称两个替换天然构成一个原子事务" in manual
    assert "两份目标版本一致" in manual


def test_document_only_request_routes_to_artifact_sync_without_development():
    workflow = read("hs-workflow-op-development/SKILL.md")
    assert "用本 workflow 新生成 X 文档" in workflow
    assert "已有算子产物使用 `artifact-sync`" in workflow
    assert "不实现、不构建、不运行板测" in workflow


def test_promotion_places_terminal_record_after_board_stages():
    promotion = read(
        "../docs/zh-CN/software/hispark-ai-operator-skills-promotion.md"
    )
    stage6 = promotion.index("6. 为全部用例生成并构建固件")
    stage7 = promotion.index("7. 全部用例烧录、串口采集和板端精度验证")
    stage8 = promotion.index("8. 统一结案")
    assert stage6 < stage7 < stage8
    assert "integrated-final" in promotion
    assert "两份文档" in promotion
    assert "OP_MANUAL_SYNC=PASS publication=final" not in promotion


def test_promotion_document_matches_document_first_stage_order():
    promotion = (
        SKILLS_ROOT.parent
        / "docs/zh-CN/software/hispark-ai-operator-skills-promotion.md"
    ).read_text(encoding="utf-8")
    flow = promotion.split("## 3. 完整确定性流程图", 1)[1].split("### 3.1", 1)[0]
    assert flow.index("mode=prepare") < flow.index("OP_PLAN_GATE")
    assert flow.index("OP_PLAN_GATE") < flow.index("integrated-initial")
    assert flow.index("integrated-initial") < flow.index("PRE_SOURCE_GATE")
    assert flow.index("PRE_SOURCE_GATE") < flow.index("stage2 apply")
    for token in (
        "source-freeze.json",
        "计划版op_spec.py",
        "operator-manual-facts.json",
        "{op}-operator-design-doc.md",
        "{op}-operator-verify-doc.md",
        "OP_MANUAL_SYNC publication=record",
        "## 6. stage3：为什么还要单独构建",
        "## 7. stage4：Host Skill 具体生成什么",
        "## 8. stage5：文档 Skill 具体生成什么",
    ):
        assert token in promotion, token
    assert "完整workflow中，下面的计划版文件已经由stage1" in promotion


def test_implement_requires_post_code_review_and_fold_checks():
    impl = read("hs-dev-op-implement/SKILL.md")
    quality = read("hs-dev-op-implement/references/code-quality-gate.md")
    gate = read("hs-dev-op-implement/scripts/gate_artifacts.py")
    for text in (impl, quality, gate):
        assert "code-review.md" in text
        assert "folding_and_rewrite_cases" in text or "折叠" in text
        assert "registration_matrix" in text or "注册键" in text
        assert "semantic_coverage" in text or "规格覆盖" in text
    assert "check_code_review" in gate


def test_operator_workflow_loads_repository_code_style_before_source_changes():
    workflow = read("hs-workflow-op-development/SKILL.md")
    impl = read("hs-dev-op-implement/SKILL.md")
    quality = read("hs-dev-op-implement/references/code-quality-gate.md")
    bundled_style = SKILLS_ROOT / "hs-dev-op-implement/references/code-style.md"

    assert bundled_style.is_file()
    apply_stage = impl.split("## step4：", 1)[1].split("## step5：", 1)[0]
    assert "首次修改任何①-⑦源码前" in apply_stage
    assert "完整读取" in apply_stage
    assert "references/code-style.md" in apply_stage
    assert "展开为绝对路径" in impl
    assert "使用者无需提供或创建" in apply_stage
    assert apply_stage.index("完整读取") < apply_stage.index("每一层动笔前")

    for token in (
        "CODE_STYLE_SOURCE",
        "CODE_STYLE_SOURCE_SHA256",
        "CODE_STYLE_AUDIT",
        "references/code-style.md",
        "逐规则审计",
    ):
        assert token in impl, token
        assert token in quality, token

    stage2 = workflow.split("## stage2：", 1)[1].split("## stage3：", 1)[0]
    stage3 = workflow.split("## stage3：", 1)[1].split("## stage4：", 1)[0]
    assert "references/code-style.md" in stage2
    assert "展开后的绝对" in stage2
    assert "不是用户需要安装的工具" in stage2
    assert "在写任何①-⑦源码前" in stage2
    assert "同一`CODE_STYLE_SOURCE`" in stage3
    assert "CODE_STYLE_AUDIT=PASS" in stage3
    assert "<opdir>/docs/code-style-audit.md" in impl
    assert "<opdir>/docs/code-style-audit.md" in quality

    rule_pattern = re.compile(r"^###\s+([A-Z]+\.\d+)", re.MULTILINE)
    bundled_rules = rule_pattern.findall(bundled_style.read_text(encoding="utf-8"))
    assert len(bundled_rules) == 65
    assert len(set(bundled_rules)) == len(bundled_rules)

    quality_gate = stage3.index("构建前由 workflow")
    build_start = stage3.index("nohup bash <hs-workflow-op-development>/scripts/build_mslite.sh")
    assert quality_gate < build_start


def test_leaf_trigger_is_explicit_and_board_stage_numbers_match():
    impl = read("hs-dev-op-implement/SKILL.md")
    board = read("hs-verify-op-board/SKILL.md")
    workflow = read("hs-workflow-op-development/SKILL.md")
    assert "explicitly requests source-only work" in impl
    assert "本 skill step0-3" in board
    assert "workflow stage6 的 sample/adaptor/固件接线" in board
    assert "stage6 默认" in workflow and "stage7 默认" in workflow


def test_full_workflow_defaults_to_automatic_full_board_matrix():
    workflow = read("hs-workflow-op-development/SKILL.md")
    board = read("hs-verify-op-board/SKILL.md")
    host = read("hs-verify-op-host/SKILL.md")
    for token in (
        "BOARD_POLICY=AUTO_ALL",
        "只有用户明确说“只做Host/不上板/不烧录”",
        "不得再询问“是否要上板”",
        "board_expected_matrix.json",
        "board_case_results.json",
        "board_verify_summary.txt",
        "BOARD_MATRIX_GATE=PASS",
        "expected=executed=pass",
    ):
        assert token in "\n".join((workflow, board, host)), token
    assert "不允许以一个或少数代表case的PASS" in board
    assert "最终用户消息必须逐行列出" in board


def test_incomplete_board_flow_cannot_be_reported_as_overall_pass():
    workflow = read("hs-workflow-op-development/SKILL.md")
    board = read("hs-verify-op-board/SKILL.md")

    for token in (
        "OP_WORKFLOW=<PASS|FAIL|INCOMPLETE|HOST_ONLY_PASS>",
        "状态：未完成（存在NOT_RUN/PENDING/RUNNING阶段）",
        "状态：仅Host范围通过（用户明确未要求板端；不是完整流程通过）",
        "FIRMWARE_MATRIX=<expected=N built=M pass=P fail=F not_run=R>",
        "BOARD_RECORDS=<expected=N recorded=M>",
        "如果板端未执行，即使Host和24份固件全部成功",
        "整体仍是`OP_WORKFLOW=INCOMPLETE`",
    ):
        assert token in workflow, token

    for forbidden_completion in (
        "已完成迁移和验证",
        "已完成开发和验证",
        "验证通过",
        "全部通过",
    ):
        assert forbidden_completion in workflow
        assert forbidden_completion in board

    assert "HOST_PASS_BOARD_NOT_RUN" not in workflow
    assert "`executed=pass+fail`" in workflow
    assert "`recorded=24 executed=0 not_run=24`" in board


def test_stage0_does_not_conflate_wsl_with_firmware_environment():
    workflow = read("hs-workflow-op-development/SKILL.md")
    for token in (
        "生成 BitShift 算子",
        "默认宣布`AUTO_ALL`",
        "HISPARK_STORAGE_ENV=<Windows|WSL|Linux>",
        "FIRMWARE_SDK_STORAGE_ENV=<Windows|WSL|Linux>",
        "FIRMWARE_BUILD_ENV=<Windows|WSL|Linux>",
        "DEVICE_IO_ENV=<Windows|WSL|Linux>",
        "路径只直接证明“文件存在哪里”",
        "file converter_lite",
        "fbb describe --json",
        "执行方式：完整开发和验证（默认）",
        "如果这次不需要开发板验证，请回复“只做电脑端验证”",
    ):
        assert token in workflow, token


def test_stage0_auto_detects_before_asking_user():
    workflow = read("hs-workflow-op-development/SKILL.md")
    for token in (
        "先自动探测",
        "可由当前会话、路径存在性和工具实测",
        "不得再次询问用户",
        "缺少`FIRMWARE_SDK_ROOT`时只询问该绝对路径",
        "收到路径后再自动判断其存储、构建和设备I/O环境",
        "完成上述Stage0只读探测后的",
        "两个环境都能成功构建同一SDK",
        "只把该项及候选证据列为",
    ):
        assert token in workflow, token
    for forbidden in (
        "开始前让用户说明代码位置和实际执行环境",
        "默认进入完整workflow时一次性收集",
        "必须把`FIRMWARE_BUILD_ENV`和`DEVICE_IO_ENV`列为“待确认”",
    ):
        assert forbidden not in workflow, forbidden


def test_stage0_requires_one_confirmation_before_any_write_or_execution():
    workflow = read("hs-workflow-op-development/SKILL.md")
    for token in (
        "EXECUTION_CONFIRM_GATE（一次总确认；确认前只读）",
        "EXECUTION_CONFIRM_GATE=PENDING",
        "EXECUTION_CONFIRM_GATE=PASS",
        "STAGE0_PREVIEW=READY",
        "TARGET_RUNTIME=<chip/board/OS/fbb-target>",
        "SDK全局及目标芯片声明的`min_cli_version`",
        "版本不足的\n   候选环境标记`BLOCKED`",
        "禁止进入stage1",
        "禁止调用下游生成/实现/验证Skill",
        "禁止创建或修改算子文档、源码、测试模型、Micro工程、SDK接线和固件",
        "请回复“确认执行”",
        "不得把最初一句\n“生成某算子”或提供SDK路径本身当成已经通过该门禁",
        "逐个烧录全部用例，读取串口输出，与电脑端标准答案比较",
    ):
        assert token in workflow, token
    assert "无需额外确认" not in workflow
    assert "不能等到Host完成后才首次询问SDK" in workflow


def test_stage0_user_message_uses_plain_language_before_internal_fields():
    workflow = read("hs-workflow-op-development/SKILL.md")
    for token in (
        "执行方式：完整开发和验证（默认）",
        "模型转换和电脑端测试",
        "固件编译",
        "开发板连接",
        "在哪个环境烧录并读取串口",
        "板上运行目标",
        "当前状态：等待你的确认",
        "请回复“确认执行”",
        "技术记录：STAGE0_PREVIEW=READY",
        "开发板连接环境”是电脑在哪个系统中通过USB/串口烧录和读取",
        "固件是后续构建出的`.fwpkg`文件",
    ):
        assert token in workflow, token
    assert workflow.index("执行方式：完整开发和验证（默认）") < workflow.index(
        "技术记录：STAGE0_PREVIEW=READY"
    )


def test_fbb_cli_sdk_toolchain_and_firmware_terms_are_distinct():
    workflow = read("hs-workflow-op-development/SKILL.md")
    for token in (
        "`fbb CLI`是提供`fbb describe/build/flash/monitor`等命令的命令行工具",
        "`固件SDK`是用户提供的芯片源码工程",
        "`交叉编译工具链`是由fbb CLI调用的",
        "`固件`是编译后生成、用于烧录的`.fwpkg`文件",
        "固件编译：<在哪个环境运行fbb CLI和交叉编译工具链>",
        "fbb CLI版本/SDK要求",
    ):
        assert token in workflow, token


def test_missing_lightweight_dependencies_are_auto_repaired_before_blocking():
    workflow = read("hs-workflow-op-development/SKILL.md")
    host = read("hs-verify-op-host/SKILL.md")
    runner = read("hs-verify-op-host/scripts/run_all_cases.py")
    for token in (
        "缺失依赖自动修复",
        "不能只\n报告“缺少xxx”就结束",
        "禁止`sudo pip`",
        "DEPENDENCY_REPAIR",
        "镜像源失败可再尝试默认源",
        "生成新`RUN_ID`",
        "管理员/root权限",
        "自动安装和验证均失败时",
    ):
        assert token in workflow, token
    assert "ONNX必须同时具备`onnx`和`onnxruntime`" in host
    assert 'ensure("onnx")' in runner
    assert 'ensure("onnxruntime")' in runner
    assert "DEPENDENCY_REPAIR=PASS" in runner


def test_converter_shared_library_failure_is_auto_repaired_in_process():
    workflow = read("hs-workflow-op-development/SKILL.md")
    host = read("hs-verify-op-host/SKILL.md")
    board = read("hs-verify-op-board/SKILL.md")
    env_setup = read("hs-workflow-mslite-env-setup/SKILL.md")
    combined = "\n".join((workflow, host, board, env_setup))
    for token in (
        "libmindspore_converter.so",
        "同一子进程",
        "其他MSLite包",
        "CONVERTER_RUNTIME_GATE=FAIL",
        "不能让用户手工`export`",
        "不修改`.bashrc`",
        "重新构建/下载",
        "新`RUN_ID`",
    ):
        assert token in combined, token
    runner = read("hs-verify-op-host/scripts/run_all_cases.py")
    micro = read("hs-verify-op-board/chips/ws63/scripts/build_micro.py")
    convert = read("hs-workflow-mslite-env-setup/scripts/convert_model.sh")
    assert "_converter_runtime_env" in runner
    assert "converter_runtime_env" in micro
    assert "converter_lite" in convert


def test_host_harness_owns_board_case_denominator():
    runner = read("hs-verify-op-host/scripts/run_all_cases.py")
    report = read("hs-verify-op-board/scripts/board_matrix_report.py")
    for token in ("BOARD_PATH_MODE", "board_expected_matrix.json", "expected_count"):
        assert token in runner
    for token in ("board_result.json", "BOARD_MATRIX_GATE", "board_case_results.json",
                  "board_verify_summary.txt"):
        assert token in report


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
