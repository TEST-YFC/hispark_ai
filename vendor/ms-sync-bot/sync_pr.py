#!/usr/bin/env python3
"""ms-sync-bot 主流程（P1，方案 §3/§4）：

  A(hispark-ai-dev) 提交 → 提取 src/mindspore-lite/** 变更 → 路径映射重写补丁
  → git apply --3way →（门禁）→ commit/push r2.8 → 台账

  apply 失败 = 触及 A/B 差异部分 → 保留现场 + 复核报告（§4.3）。

用法：
  sync_pr.py list                                 列出 A 侧可同步单元
  sync_pr.py sync <unit> [--push] [--no-gate]     同步一个单元到 B（默认只 commit 不 push）
  sync_pr.py sync-from <unit> [--push] [--no-gate] [--dry-run]
                                                  从某单元起批量同步到最新；每笔 quick 门禁，
                                                  最后一笔后统一 full；--push 仅在 full 通过后推送
  sync_pr.py auto [--init <unit>] [--push] [--dry-run]
                                                  一键式：维护同步节点 cursor，自动同步其后单元
                                                  （自动 fetch+快进 A/B 仓；外壳脚本 sync_auto.sh）
  sync_pr.py replay --commit <hash> [--b-base <hash>] [--compare <hash>] [--keep]
                                                  离线重放：独立 worktree 应用并与人工作业对账
  sync_pr.py status                               查看台账
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

import commit_watcher as watcher
from path_map import map_path, ACTION_MAP, ACTION_IGNORE, ACTION_GENERATED

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(TOOL_DIR, "sync_state.json")
REPORT_DIR = os.path.join(TOOL_DIR, "report")
A_SCOPE = "src/mindspore-lite/"          # A 仓提取范围

DIFF_GIT_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")


# ---------------------------------------------------------------- 基础设施

def load_config():
    with open(os.path.join(TOOL_DIR, "config.json")) as f:
        return json.load(f)


def git(repo, *args, check=True, input_text=None):
    r = subprocess.run(["git", "-C", repo] + list(args),
                       capture_output=True, text=True, input=input_text)
    if check and r.returncode != 0:
        raise RuntimeError("git -C %s %s failed:\n%s" % (repo, " ".join(args), r.stderr.strip()))
    return r.stdout


def git_bytes(repo, *args, check=True):
    """字节模式（二进制安全的 diff 输出用）。"""
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError("git -C %s %s failed:\n%s" % (repo, " ".join(args), r.stderr.decode(errors="replace").strip()))
    return r.stdout


def load_ledger():
    if os.path.exists(LEDGER):
        with open(LEDGER) as f:
            return json.load(f)
    return {"units": {}}


def save_ledger(led):
    with open(LEDGER, "w") as f:
        json.dump(led, f, ensure_ascii=False, indent=2, sort_keys=True)


def record(led, uid, **fields):
    ent = led["units"].setdefault(uid, {})
    ent.update(fields)
    ent["updated_at"] = datetime.date.today().isoformat()
    save_ledger(led)
    return ent


def load_protected():
    """protected_files.yaml → (protected 集合, ignore_forever 集合)"""
    import yaml
    with open(os.path.join(TOOL_DIR, "protected_files.yaml")) as f:
        data = yaml.safe_load(f)
    return set(data.get("protected") or []), set(data.get("ignore_forever") or [])


# ---------------------------------------------------------------- 提取与重写

def extract_patch(repo_a, base, head):
    """A 仓 base..head 限定同步范围的原始 diff（二进制安全，禁 rename 检测）。"""
    raw = git_bytes(repo_a, "-c", "core.quotePath=false", "diff",
                    "--no-renames", "--binary", base, head, "--", A_SCOPE)
    # surrogateescape 保证二进制段（GIT binary patch 为 base85 ASCII，偶有原始字节）无损往返
    return raw.decode("utf-8", errors="surrogateescape")


def rewrite_patch(raw):
    """按 path_map 重写补丁路径，丢弃 ignore/generated 的文件段。

    返回 (patch_text, stats)；stats 含 map/ignore/generated 三类清单。
    """
    out, stats = [], {"map": [], "ignore": [], "generated": []}
    section, apath = [], None

    def flush():
        if apath is None:
            return
        bpath, action, reason = map_path(apath)
        item = (apath, bpath, reason)
        bucket = {"map": "map", "ignore": "ignore", "generated": "generated"}[action]
        if bucket != "map":
            stats[bucket].append({"a": apath, "reason": reason})
        else:
            stats["map"].append(bpath)
        if action != ACTION_MAP:
            return
        for ln in section:
            out.append(rewrite_line(ln, apath, bpath))

    def rewrite_line(ln, apath, bpath):
        m = DIFF_GIT_RE.match(ln)
        if m:
            return "diff --git a/%s b/%s" % (bpath, bpath)
        if ln.startswith("--- a/"):
            return "--- a/" + bpath
        if ln.startswith("+++ b/"):
            return "+++ b/" + bpath
        if ln.startswith("Binary files a/") and ln.rstrip().endswith("differ"):
            return "Binary files a/%s and b/%s differ" % (bpath, bpath)
        return ln

    for ln in raw.split("\n"):
        if ln.startswith("diff --git "):
            flush()
            m = DIFF_GIT_RE.match(ln)
            apath = m.group(1) if m else None
            section = [ln]
        elif apath is not None:
            section.append(ln)
    flush()

    patch = "\n".join(out)
    return patch, stats


def classify_conflicts(stderr, protected):
    """从 git apply 的报错提取冲突文件，并标注是否环境适配文件（§4.3 复核报告）。"""
    hits = {}
    for ln in stderr.splitlines():
        m = re.match(r"^(?:error: )?(?:patch failed|Applied patch .*? does not match|No such file or directory).*?:\s*(\S.*)$", ln)
        if m:
            hits[m.group(1).strip()] = ln.strip()
        m2 = re.search(r"error: ([^:]+): (?:could not find blob|does not match index)", ln)
        if m2:
            hits[m2.group(1).strip()] = ln.strip()
    out = []
    for path, err in hits.items():
        clean = path.lstrip("ab/")
        out.append({"file": clean, "error": err,
                    "protected": clean in protected})
    return out


# ---------------------------------------------------------------- commit message

def b_commit_message(unit, cfg):
    """B 侧提交描述。

    PR 单元（2026-09-04 定稿）：只保留 A 侧 PR 的 description 部分，
    如 "[Hisilicon_sh] Fix Conv3x3 Multi Batch Int8 bug"（不带 [CodeHub MR !N]
    前缀、不带 body 里的 revert 元数据）。追溯信息（A 侧 hash/MR 号）只存台账。
    legacy 批量单元保持原格式（过渡期形态，不再新增）。
    """
    if unit["kind"] == "pr":
        return unit["title"]
    a_full = git(cfg["repo_a"], "rev-parse", unit["commit"]).strip()
    lines = ["sync %s: %s" % (watcher.unit_id(unit), unit["title"]), ""]
    if unit.get("match_id"):
        lines.append("Match-id: %s" % unit["match_id"])
    lines.append("Synced-From: HiSpark/hispark-ai-dev@%s" % a_full)
    lines.append("(synced by ms-sync-bot)")
    return "\n".join(lines)


# ---------------------------------------------------------------- 子命令

def resolve_unit(cfg, uid):
    units, _ = watcher.scan_units(cfg["repo_a"])
    for u in units:
        if watcher.unit_id(u) == uid:
            return u
    # 直接按 commit hash 前缀匹配（如 286084f）
    for u in units:
        if u["commit"].startswith(uid):
            return u
    # 单元 ID 前缀匹配（legacy@<hash 前缀>）
    for u in units:
        if watcher.unit_id(u).startswith(uid) or uid.startswith(watcher.unit_id(u)):
            return u
    return None


def cmd_list(cfg):
    units, warns = watcher.scan_units(cfg["repo_a"])
    led = load_ledger()
    for u in units:
        uid = watcher.unit_id(u)
        st = led["units"].get(uid, {}).get("status", "-")
        print("%-22s %-14s %-9s %s" % (uid, u["commit"][:12], st, u["title"][:60]))
    if warns:
        print("\n⚠ 格式走样告警：")
        for h, s in warns:
            print("  %s %s" % (h, s))
    return 0


def cmd_status(cfg):
    led = load_ledger()
    cur = led.get("cursor")
    if cur:
        print("cursor（同步节点）: %s  (%s)" % (cur.get("unit"), cur.get("a_commit", "")[:12]))
    if not led["units"]:
        print("台账为空")
        return 0
    for uid, ent in sorted(led["units"].items()):
        print("%-24s %-14s b=%s %s" % (
            uid, ent.get("status", "?"),
            (ent.get("b_commit") or "-")[:12], ent.get("note", "")))
    return 0


def prepare_unit(cfg, unit, tag):
    """提取+重写，落盘补丁与统计。返回 (patch_text, stats)。"""
    raw = extract_patch(cfg["repo_a"], unit["base"], unit["commit"])
    patch, stats = rewrite_patch(raw)
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(os.path.join(REPORT_DIR, "%s.patch" % tag), "w",
              encoding="utf-8", errors="surrogateescape") as f:
        f.write(patch)
    with open(os.path.join(REPORT_DIR, "%s.stats.json" % tag), "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return patch, stats


def check_branch(cfg):
    repo_b = cfg["repo_b"]
    branch = git(repo_b, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch != cfg["b_branch"]:
        print("B 仓当前在 %s，需在 %s 上执行" % (branch, cfg["b_branch"]))
        return False
    return True


def run_gate(mode, repo_b):
    """返回 (退出码, stderr)。"""
    g = subprocess.run(["bash", os.path.join(TOOL_DIR, "gate.sh"), mode, repo_b],
                       capture_output=True, text=True)
    print(g.stdout)
    return g.returncode, g.stderr


def sync_one(cfg, unit, led, push=False, no_gate=False, batch=False):
    """同步单个已解析单元（前置：B 已在目标分支）。

    返回 (status, exit_code)；status ∈ synced/skipped/already/maint_skip/
    apply_conflict/gate_failed。
    """
    if unit["kind"] == "maint":
        print("跳过 MAINT 单元（%s）" % unit["title"])
        return "maint_skip", 0
    real_uid = watcher.unit_id(unit)
    if led["units"].get(real_uid, {}).get("status") == "synced":
        print("%s 已同步（台账），跳过" % real_uid)
        return "already", 0

    repo_b = cfg["repo_b"]
    patch, stats = prepare_unit(cfg, unit, real_uid.replace("/", "_"))
    print("映射：%d 个文件，忽略 %d，生成物 %d" %
          (len(stats["map"]), len(stats["ignore"]), len(stats["generated"])))
    if not stats["map"]:
        record(led, real_uid, status="skipped", note="no mapped files")
        print("无可映射文件，记 skipped")
        return "skipped", 0

    # 工作区安全：补丁涉及路径与脏文件求交
    dirty = set(l[3:] for l in git(repo_b, "status", "--porcelain").splitlines() if l.strip())
    clash = [p for p in stats["map"] if p in dirty]
    if clash:
        print("B 工作区存在与补丁冲突的脏文件：%s" % clash)
        return "dirty", 2

    rc, out, err = apply_in(repo_b, patch)
    if rc != 0:
        protected, _ = load_protected()
        conflicts = classify_conflicts(err, protected)
        report_path = write_conflict_report(real_uid, unit, stats, err, conflicts)
        record(led, real_uid, status="apply_conflict",
               a_commit=unit["commit"], conflicts=[c["file"] for c in conflicts])
        print("❌ apply 失败（触及 A/B 差异部分）→ %s" % report_path)
        return "apply_conflict", 1

    print("✅ apply 成功")

    if not no_gate:
        rc, err = run_gate("quick", repo_b)
        if rc != 0:
            record(led, real_uid, status="gate_failed", a_commit=unit["commit"],
                   note="现场已保留（未 commit）")
            print("❌ quick 门禁失败，现场保留，人工处理后可重跑")
            print(err)
            return "gate_failed", 1

    msg = b_commit_message(unit, cfg)
    git(repo_b, "add", "-A")
    git(repo_b, "commit", "-m", msg)
    b_head = git(repo_b, "rev-parse", "HEAD").strip()
    record(led, real_uid, status="synced", a_commit=unit["commit"], b_commit=b_head,
           mapped=len(stats["map"]), ignored=len(stats["ignore"]), generated=len(stats["generated"]))
    print("✅ 已提交 %s：%s" % (b_head[:12], msg.splitlines()[0]))

    if push:
        git(repo_b, "push", cfg.get("b_push_remote", "origin"), cfg["b_branch"])
        print("✅ 已推送 %s %s" % (cfg.get("b_push_remote", "origin"), cfg["b_branch"]))
    elif not batch:
        print("（未 push，确认后执行: git -C %s push origin %s）" % (repo_b, cfg["b_branch"]))
    return "synced", 0


def cmd_sync(cfg, uid, push=False, no_gate=False):
    unit = resolve_unit(cfg, uid)
    if not unit:
        print("未找到单元 %s（用 list 查看）" % uid)
        return 2
    if not check_branch(cfg):
        return 2
    led = load_ledger()
    status, rc = sync_one(cfg, unit, led, push=push, no_gate=no_gate)
    return rc


def run_batch(cfg, todo, led, push=False, no_gate=False, on_unit_done=None):
    """批量执行单元：quick 逐笔 → 最后一笔后统一 full →（可选）full 通过后统一 push。

    on_unit_done(unit) 在每个单元处理完毕（含跳过/已同步）后调用，auto 模式用于推进 cursor。
    返回 (exit_code, committed_unit_ids)。
    """
    print("批量同步：%d 个单元（%s → %s），每笔 quick 门禁，最后统一 full" %
          (len(todo), watcher.unit_id(todo[0]), watcher.unit_id(todo[-1])))
    committed = []
    for i, u in enumerate(todo):
        print("\n===== [%d/%d] %s =====" % (i + 1, len(todo), watcher.unit_id(u)))
        status, rc = sync_one(cfg, u, led, no_gate=no_gate, batch=True)
        if rc == 0 and on_unit_done is not None:
            on_unit_done(u)
        if status == "synced":
            committed.append(watcher.unit_id(u))
        if rc != 0:
            print("\n⏹ 批量中止于 %s（后序单元依赖前序；修复后重跑同一命令可续，已同步的会跳过）"
                  % watcher.unit_id(u))
            return rc, committed

    batch_id = "batch:%s..%s" % (watcher.unit_id(todo[0]), watcher.unit_id(todo[-1]))
    if no_gate:
        print("\n--no-gate：跳过全部门禁（quick/full 均未执行）")
        if committed:
            record(led, batch_id, status="gates_skipped", units=committed,
                   note="⚠ 门禁被 --no-gate 跳过，push 前建议补跑 gate.sh")
    elif not committed:
        print("\n无新同步单元，跳过 full 门禁")
        record(led, batch_id, status="noop", note="all units already synced")
    else:
        print("\n===== FULL 门禁（全量构建，30min+ 量级）=====")
        rc, err = run_gate("full", cfg["repo_b"])
        record(led, batch_id,
               status="full_gate_pass" if rc == 0 else "full_gate_failed",
               units=committed)
        if rc != 0:
            print("❌ full 门禁失败（代码已 commit、未 push）：请修复后重跑验证，或人工确认后手动推送")
            print(err)
            return 1, committed
        print("✅ full 门禁通过")

    if push:
        git(cfg["repo_b"], "push", cfg.get("b_push_remote", "origin"), cfg["b_branch"])
        print("✅ 已推送 %s %s" % (cfg.get("b_push_remote", "origin"), cfg["b_branch"]))
    else:
        print("（未 push，确认后执行: git -C %s push origin %s）"
              % (cfg["repo_b"], cfg["b_branch"]))
    return 0, committed


def cmd_sync_from(cfg, uid, push=False, no_gate=False, dry_run=False):
    """从某一单元起批量同步到最新：每笔过 quick 门禁，最后一笔之后统一跑 full。

    中途失败即中止（后序单元依赖前序，禁止跳跃）；已同步单元经台账跳过，
    修复后重跑同一命令可续。--push 时仅在 full 通过后推送。
    """
    units, _ = watcher.scan_units(cfg["repo_a"])
    start = resolve_unit(cfg, uid)
    if not start:
        print("未找到起始单元 %s（用 list 查看）" % uid)
        return 2
    idx = next((i for i, u in enumerate(units) if u["commit"] == start["commit"]), None)
    if idx is None:
        print("起始单元不在扫描结果中：%s" % uid)
        return 2
    todo = units[idx:]
    if dry_run:
        led = load_ledger()
        print("计划同步 %d 个单元（%s → %s）：" %
              (len(todo), watcher.unit_id(todo[0]), watcher.unit_id(todo[-1])))
        for i, u in enumerate(todo):
            st = led["units"].get(watcher.unit_id(u), {}).get("status", "待同步")
            print("  [%d/%d] %-22s %-12s %s" %
                  (i + 1, len(todo), watcher.unit_id(u), u["commit"][:12], st))
        print("门禁计划：每笔 quick，最后统一 full（30min+）")
        return 0
    if not check_branch(cfg):
        return 2
    led = load_ledger()

    print("批量同步：%d 个单元（%s → %s），每笔 quick 门禁，最后统一 full" %
          (len(todo), watcher.unit_id(todo[0]), watcher.unit_id(todo[-1])))
    rc, _committed = run_batch(cfg, todo, load_ledger(), push=push, no_gate=no_gate)
    return rc


def update_repos(cfg):
    """一键模式：更新本地 A/B 仓（fetch + ff-only 快进）。

    返回 None 表示成功；返回字符串为中止原因。
    fetch 失败（离线等）降级为告警并继续用本地状态；快进失败（本地分叉/脏）则中止。
    """
    a, b = cfg["repo_a"], cfg["repo_b"]
    b_remote = cfg.get("b_push_remote", "origin")
    try:
        rf = subprocess.run(["git", "-C", a, "fetch", "origin"],
                            capture_output=True, text=True)
        if rf.returncode != 0:
            print("⚠ A 仓 fetch 失败（离线？继续用本地状态）：%s" % rf.stderr.strip()[:120])
        else:
            if git(a, "rev-parse", "--abbrev-ref", "HEAD").strip() != "master":
                git(a, "checkout", "master")
            git(a, "merge", "--ff-only", "origin/master")
    except RuntimeError as e:
        return "A 仓更新失败（需人工处理）：%s" % e
    try:
        rb = subprocess.run(["git", "-C", b, "fetch", b_remote],
                            capture_output=True, text=True)
        if rb.returncode != 0:
            print("⚠ B 仓 fetch 失败（离线？继续用本地状态）：%s" % rb.stderr.strip()[:120])
        else:
            if git(b, "rev-parse", "--abbrev-ref", "HEAD").strip() != cfg["b_branch"]:
                git(b, "checkout", cfg["b_branch"])
            git(b, "merge", "--ff-only", "%s/%s" % (b_remote, cfg["b_branch"]))
    except RuntimeError as e:
        return "B 仓更新失败（需人工处理）：%s" % e
    return None


def cmd_auto(cfg, push=False, no_gate=False, dry_run=False, init=None):
    """一键同步：维护同步节点（cursor），每次执行自动同步该节点之后的所有单元。

    cursor 存于台账顶层 "cursor" 字段 = 最后一个已处理单元的 A 侧 commit。
    首次使用需 --init <unit> 声明"已同步到哪"；每个单元处理成功（含跳过）后推进 cursor，
    失败则停在 cursor 处，修复后重跑即续。
    """
    led = load_ledger()
    if init:
        unit = resolve_unit(cfg, init)
        if not unit:
            print("未找到单元 %s（用 list 查看）" % init)
            return 2
        led["cursor"] = {"a_commit": unit["commit"], "unit": watcher.unit_id(unit)}
        save_ledger(led)
        print("cursor 已初始化 → %s（%s），下次执行将同步其后的单元"
              % (watcher.unit_id(unit), unit["commit"][:12]))
        return 0

    cur = led.get("cursor")
    if not cur:
        print("未初始化同步节点。首次使用先执行：\n"
              "  python3 sync_pr.py auto --init <unit|hash>\n"
              "（语义：已同步到该单元，含；之后每次执行自动同步其后的单元）")
        return 2

    if not dry_run:
        err = update_repos(cfg)
        if err:
            print("❌ %s" % err)
            return 2

    units, _ = watcher.scan_units(cfg["repo_a"])
    idx = next((i for i, u in enumerate(units)
                if u["commit"] == cur.get("a_commit")), None)
    if idx is None:
        print("❌ cursor 指向的提交 %s 不在当前扫描结果中（历史变动？），"
              "请重新对位：python3 sync_pr.py auto --init <unit>" % cur.get("a_commit", "?")[:12])
        return 2
    todo = units[idx + 1:]

    if not todo:
        print("✅ 已是最新（cursor: %s）" % cur.get("unit"))
        return 0

    if dry_run:
        print("cursor: %s（%s），其后待同步 %d 个单元：" %
              (cur.get("unit"), cur.get("a_commit", "")[:12], len(todo)))
        for i, u in enumerate(todo):
            st = led["units"].get(watcher.unit_id(u), {}).get("status", "待同步")
            print("  [%d/%d] %-22s %-12s %s" %
                  (i + 1, len(todo), watcher.unit_id(u), u["commit"][:12], st))
        print("门禁计划：每笔 quick，最后统一 full（30min+）")
        return 0

    def on_done(u):
        led["cursor"] = {"a_commit": u["commit"], "unit": watcher.unit_id(u)}
        save_ledger(led)

    rc, committed = run_batch(cfg, todo, led, push=push, no_gate=no_gate,
                              on_unit_done=on_done)
    if rc == 0:
        print("\ncursor → %s" % led.get("cursor", {}).get("unit"))
    return rc


def apply_in(worktree, patch_text):
    p = subprocess.run(
        ["git", "-C", worktree, "apply", "--3way", "--binary", "--whitespace=nowarn", "-"],
        input=patch_text.encode("utf-8", "surrogateescape"), capture_output=True)
    return (p.returncode,
            p.stdout.decode(errors="replace"),
            p.stderr.decode(errors="replace"))


def write_conflict_report(uid, unit, stats, err, conflicts):
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, "%s.conflict.md" % uid.replace("/", "_"))
    with open(path, "w") as f:
        f.write("# %s apply 冲突复核报告\n\n" % uid)
        f.write("- A 提交: %s %s\n" % (unit["commit"], unit["title"]))
        f.write("- 映射 %d / 忽略 %d / 生成物 %d\n\n" %
                (len(stats["map"]), len(stats["ignore"]), len(stats["generated"])))
        f.write("## 冲突文件（protected=环境适配层，人工确认移植方式）\n\n")
        for c in conflicts:
            f.write("- `%s` %s\n  - %s\n" % (c["file"], "🛡 protected" if c["protected"] else "", c["error"]))
        if not conflicts:
            f.write("（未能从报错解析出文件，见下方原始输出）\n")
        f.write("\n## git apply 原始输出\n\n```\n%s\n```\n" % err)
    return path


def cmd_replay(cfg, a_commit, b_base=None, compare=None, keep=False):
    """离线重放：在独立 worktree 上应用单元补丁，与 B 侧人工作业对账。"""
    unit = resolve_unit(cfg, a_commit) or dict(
        kind="legacy", title="(manual commit)", commit=a_commit,
        base=git(cfg["repo_a"], "rev-parse", a_commit + "^").strip())
    real_uid = watcher.unit_id(unit)
    repo_b = cfg["repo_b"]
    tag = real_uid.replace("/", "_")

    patch, stats = prepare_unit(cfg, unit, tag)
    print("单元 %s：映射 %d，忽略 %d，生成物 %d" %
          (real_uid, len(stats["map"]), len(stats["ignore"]), len(stats["generated"])))

    wt = os.path.join(REPORT_DIR, "wt-%s" % tag)
    if os.path.exists(wt):
        git(repo_b, "worktree", "remove", "--force", wt)
    if b_base:
        git(repo_b, "worktree", "add", "--detach", wt, b_base)
    else:
        git(repo_b, "worktree", "add", "--detach", wt)
    try:
        rc, out, err = apply_in(wt, patch)
        if rc != 0:
            protected, _ = load_protected()
            conflicts = classify_conflicts(err, protected)
            path = write_conflict_report(real_uid, unit, stats, err, conflicts)
            print("❌ 重放 apply 失败 → %s" % path)
            return 1
        print("✅ 重放 apply 成功")
        git(wt, "add", "-A")

        if not compare:
            diff = git(wt, "diff", "--cached", "--stat")
            print("\n== 相对 base 的变更（未指定 --compare）==\n%s" % diff)
            return 0

        # 对账：我们的结果(index) vs 人工同步提交
        ours_tree = git(wt, "write-tree").strip()
        full = git(repo_b, "diff", "--stat", ours_tree, compare)
        names = git(repo_b, "diff", "--name-status", ours_tree, compare)
        report = os.path.join(REPORT_DIR, "%s.replay.md" % tag)
        with open(report, "w") as f:
            f.write("# %s 重放对账\n\n- ours(tree) vs manual(%s)\n\n```\n%s\n```\n\n"
                    % (real_uid, compare, names))
        print("\n== 对账：工具结果 vs 人工 %s ==" % compare)
        print(full if full.strip() else "（完全一致）")
        print("明细: %s" % report)
        led = load_ledger()
        record(led, "replay:" + real_uid, status="done", a_commit=unit["commit"],
               compare=compare,
               note="identical" if not full.strip() else "diff %s lines" % len(full.splitlines()))
        return 0
    finally:
        if keep:
            print("（worktree 保留: %s）" % wt)
        else:
            git(repo_b, "worktree", "remove", "--force", wt)


def main():
    ap = argparse.ArgumentParser(description="A→B PR 同步工具（P1）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("status")
    sp = sub.add_parser("sync")
    sp.add_argument("unit")
    sp.add_argument("--push", action="store_true")
    sp.add_argument("--no-gate", action="store_true")
    sf = sub.add_parser("sync-from")
    sf.add_argument("unit", help="起始单元（含），同步到最新")
    sf.add_argument("--push", action="store_true")
    sf.add_argument("--no-gate", action="store_true")
    sf.add_argument("--dry-run", action="store_true", help="只列出计划，不执行")
    au = sub.add_parser("auto", help="一键同步 cursor 之后的单元")
    au.add_argument("--init", metavar="UNIT", help="初始化/重设 cursor：声明已同步到该单元（含）")
    au.add_argument("--push", action="store_true")
    au.add_argument("--no-gate", action="store_true")
    au.add_argument("--dry-run", action="store_true", help="只列出计划，不执行（纯本地读取）")
    rp = sub.add_parser("replay")
    rp.add_argument("--commit", required=True)
    rp.add_argument("--b-base")
    rp.add_argument("--compare")
    rp.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    if args.cmd == "list":
        return cmd_list(cfg)
    if args.cmd == "status":
        return cmd_status(cfg)
    if args.cmd == "sync":
        return cmd_sync(cfg, args.unit, push=args.push, no_gate=args.no_gate)
    if args.cmd == "sync-from":
        return cmd_sync_from(cfg, args.unit, push=args.push, no_gate=args.no_gate,
                             dry_run=args.dry_run)
    if args.cmd == "auto":
        return cmd_auto(cfg, push=args.push, no_gate=args.no_gate,
                        dry_run=args.dry_run, init=args.init)
    if args.cmd == "replay":
        return cmd_replay(cfg, args.commit, args.b_base, args.compare, args.keep)
    return 2


if __name__ == "__main__":
    sys.exit(main())
