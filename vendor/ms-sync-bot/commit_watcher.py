#!/usr/bin/env python3
"""A 仓变更单元扫描（方案 §4.1 / §8.2）。

单元类型：
  pr     —— `Repo Sync PR#<N>: <标题>`（A 侧按 PR 拆开后的正式形态）
  legacy —— `HiSpark.AI ... Repo Sync <日期>` 批量提交（过渡期，台账标 legacy_batch）
  maint  —— `Repo Sync MAINT: <...>`（默认不进 B）

同时输出"疑似 Repo Sync 但格式不匹配"的告警清单，防格式走样导致单元静默漏同步。
"""
import re
import subprocess

PR_RE = re.compile(r"^Repo Sync PR#(\d+):\s*(.+)$")
PR_FIXUP_RE = re.compile(r"^Repo Sync PR#(\d+) fixup:\s*(.+)$")
# A 侧实际启用格式（2026-09-04 实测）：[CodeHub MR !N] Description: <标题>
CODEHUB_RE = re.compile(r"^\[CodeHub MR !(\d+)\]\s*Description:\s*(.+)$")
MAINT_RE = re.compile(r"^Repo Sync MAINT:", re.I)
LEGACY_RE = re.compile(r"^HiSpark\.AI.*Repo Sync", re.I)
ANY_SYNC_RE = re.compile(r"Repo Sync", re.I)

TRAILERS = {
    "upstream_pr": re.compile(r"^Upstream-PR:\s*(.+)$", re.M),
    "author": re.compile(r"^Author:\s*(.+)$", re.M),
    "type": re.compile(r"^Type:\s*(.+)$", re.M),
    "ticket": re.compile(r"^Ticket:\s*(.+)$", re.M),
    "match_id": re.compile(r"^Match-id:\s*([0-9a-f]{40})\s*$", re.M),
}
MATCH_ID_LEGACY_RE = re.compile(r"^Match-id-([0-9a-f]{40})\s*$", re.M)


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo] + list(args),
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (args, r.stderr.strip()))
    return r.stdout


def parse_trailers(full_msg):
    meta = {}
    for key, rx in TRAILERS.items():
        m = rx.search(full_msg)
        if m:
            meta[key] = m.group(1).strip()
    if "match_id" not in meta:
        m = MATCH_ID_LEGACY_RE.search(full_msg)
        if m:
            meta["match_id"] = m.group(1)
    return meta


def scan_units(repo_a, limit=500, ref="master"):
    """全历史扫描（Repo Sync 提交在侧支上、经 merge 进主线，first-parent 链不含它们），
    返回按时间正序的单元列表。"""
    # 字段分隔 \x00，记录分隔 \x1e
    fmt = "%H%x00%P%x00%an%x00%ad%x00%s%x00%b%x1e"
    out = git(repo_a, "log", "-n", str(limit), "--date-order",
              "--date=short", "--format=" + fmt, ref)
    units, warnings = [], []
    for record in out.split("\x1e"):
        if not record.strip():
            continue
        parts = record.lstrip("\n").split("\x00")
        if len(parts) < 6:
            continue
        h, parents, an, ad, subject, body = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        base = parents.split(" ")[0] if parents else ""
        subject = subject.strip()

        m = CODEHUB_RE.match(subject)
        if m:
            pr = int(m.group(1))
            u = dict(kind="pr", pr=pr, fixup=False, title=m.group(2).strip(),
                     subject=subject, commit=h, base=base, author_name=an, date=ad,
                     upstream_pr="CodeHub MR !%d" % pr)
            u.update(parse_trailers(subject + "\n" + body))
            units.append(u)
            continue
        m = PR_FIXUP_RE.match(subject) or PR_RE.match(subject)
        if m:
            fixup = bool(PR_FIXUP_RE.match(subject))
            pr = int(m.group(1))
            title = m.group(2).strip()
            u = dict(kind="pr", pr=pr, fixup=fixup, title=title,
                     subject=subject, commit=h, base=base, author_name=an, date=ad)
            u.update(parse_trailers(subject + "\n" + body))
            units.append(u)
            continue
        if MAINT_RE.match(subject):
            units.append(dict(kind="maint", title=subject, subject=subject,
                              commit=h, base=base, author_name=an, date=ad))
            continue
        if LEGACY_RE.match(subject):
            u = dict(kind="legacy", title=subject, subject=subject,
                     commit=h, base=base, author_name=an, date=ad)
            u.update(parse_trailers(subject + "\n" + body))
            units.append(u)
            continue
        if ANY_SYNC_RE.search(subject):
            warnings.append((h[:12], subject))

    units.reverse()  # 时间正序：旧→新

    # 同一 MR 多次出现（历史 revert/重应用循环）：仅保留最后一笔（净内容），
    # 其余（含被 revert 的中间笔）丢弃并告警。后续无 revert 则不会触发。
    last = {}
    for i, u in enumerate(units):
        if u["kind"] == "pr":
            last[u["pr"]] = i
    drop = set()
    for i, u in enumerate(units):
        if u["kind"] == "pr" and i != last[u["pr"]]:
            drop.add(i)
            warnings.append((u["commit"][:12],
                             "MR !%d 重复（历史 revert 循环），保留最后一笔 %s" %
                             (u["pr"], units[last[u["pr"]]]["commit"][:12])))
    if drop:
        units = [u for i, u in enumerate(units) if i not in drop]
    return units, warnings


def unit_id(u):
    if u["kind"] == "pr":
        return "PR#%d" % u["pr"]
    if u["kind"] == "legacy":
        return "legacy@%s" % u["commit"][:12]
    return "maint@%s" % u["commit"][:12]


def format_unit(u):
    tags = []
    if u["kind"] == "pr":
        tags.append("fixup" if u.get("fixup") else "pr")
        if u.get("upstream_pr"):
            tags.append(u["upstream_pr"])
    else:
        tags.append(u["kind"])
    return "%-18s %-12s %s %-40s %s" % (
        unit_id(u), u["commit"][:12], u.get("date", ""), u["title"][:40], ",".join(tags))


if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    units, warns = scan_units(repo)
    print("== 单元（时间正序，共 %d）==" % len(units))
    for u in units:
        print(format_unit(u))
    if warns:
        print("\n== ⚠ 格式走样告警（含 Repo Sync 字样但无法解析）==")
        for h, s in warns:
            print("  %s %s" % (h, s))
