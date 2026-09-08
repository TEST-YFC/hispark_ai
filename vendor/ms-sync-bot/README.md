# ms-sync-bot

A（`HiSpark/hispark-ai-dev`）→ B（`xxx/mindspore-lite`，fork of `HiSpark/mindspore-lite` r2.8）
的按 PR 同步工具。

---

## 1. 环境要求

| 项 | 要求 | 说明 |
|---|---|---|
| Python | ≥ 3.10 | 仅标准库 + `pyyaml`（`pip install pyyaml`） |
| git | 任意较新版本 | 需支持 `apply --3way --binary` |
| SSH | A 仓只读 + B 仓 push | 凭据配置在运行机器的 `~/.ssh`；**不需要 PAT**（P2/P3 的 API 场景才需要） |
| lint 工具 | 可选 | `cpplint`、`cppcheck` 装了则门禁生效，未装则告警通过 |

---

## 2. 目录结构与文件说明

```
ms-sync-bot/
├── sync_auto.sh         # ★ 一键同步入口（包装 sync_pr.py auto，可挂 cron）
├── sync_pr.py           # 主入口：list / sync / sync-from / auto / replay / status
├── commit_watcher.py    # A 仓单元扫描（可独立运行调试）
├── path_map.py          # 路径映射与过滤规则（可独立运行自测）
├── gate.sh              # 门禁（quick/full 两档）
├── config.json          # 运行配置（见 §5）
├── protected_files.yaml # 环境适配文件清单（复核报告标注用）
├── sync_state.json      # 台账 + 同步节点 cursor（自动维护，勿手工编辑除非补录）
└── report/              # 补丁、统计、冲突报告、重放 worktree（自动生成）
```

`report/` 下按单元产出：

| 文件 | 内容 |
|---|---|
| `<id>.patch` | 路径重写后、待应用到 B 的补丁 |
| `<id>.stats.json` | 映射/忽略/生成物三类文件清单 |
| `<id>.conflict.md` | apply 失败时的复核报告（冲突文件 + 是否环境适配层标注 + git 原始报错） |
| `<id>.replay.md` | replay 对账明细 |
| `wt-<id>/` | replay 的临时 worktree（`--keep` 时保留） |

---

## 3. 命令详细说明

### 3.1 `list` —— 查看可同步单元

```bash
python3 sync_pr.py list
```

输出 A 仓全部单元（时间正序）+ 台账状态 + 格式走样告警。

```
legacy@f7fca78a60f6    f7fca78a60f6   -         HiSpark.AI Repo Sync 2026-06-18_00-00-44
legacy@286084f868ff    286084f868ff   -         HiSpark.AI mindspore-lite Repo Sync 2026-08-21_00-00-40
PR#57                 1a2b3c4d5e6f   synced    Repo Sync PR#57: [Hisilicon_sh] LSTM ...
⚠ 格式走样告警：
  abc12345ef01 HiSpark.AI repo sync（大小写异常/无日期）
```

状态列：`-` 未同步；`synced` 已同步；`apply_conflict` 待人工；`gate_failed` 门禁失败；`skipped` 无可映射文件。

### 3.2 `sync` —— 同步一个单元到 B

```bash
python3 sync_pr.py sync <unit> [--push] [--no-gate]
```

| 参数 | 说明 |
|---|---|
| `<unit>` | 三种写法：`PR#57`（正式单元）/ `legacy@286084f` 或简写 `286084f`（hash 前缀）/ `maint@…`（会拒绝并提示） |
| `--push` | commit 后立即 `git push origin r2.8`；**缺省只 commit 不 push**，人工确认后再推 |
| `--no-gate` | 跳过门禁（仅调试，正式同步勿用） |

执行流程与退出码：

```
前置检查（B 在 r2.8 分支；工作区脏文件与补丁路径无交集）
→ 提取 A 变更（仅 src/mindspore-lite/**）→ 路径重写 → report/<id>.patch
→ git apply --3way
   ├─ 成功 → gate.sh quick
   │         ├─ 过 → commit（message 自动生成）→ [push] → 台账 synced     退出码 0
   │         └─ 不过 → 现场保留（未 commit）→ 台账 gate_failed            退出码 1
   └─ 失败 → report/<id>.conflict.md → 台账 apply_conflict                退出码 1
```

其他退出码：`2` = 用法/前置检查失败（单元不存在、不在目标分支、脏文件冲突、MAINT 单元）。

**同步前请先更新本地 A 仓**（工具不自动 fetch）：

```bash
git -C /root/AI/hispark_ai_dev/hispark-ai-dev fetch origin && \
git -C /root/AI/hispark_ai_dev/hispark-ai-dev checkout master && \
git -C /root/AI/hispark_ai_dev/hispark-ai-dev pull --ff-only
```

**幂等**：台账已记 `synced` 的单元重跑会直接跳过。补丁为空的单元（如 `ai_samples Repo Sync`
只动 src/samples）自动记 `skipped`。

### 3.3 `sync-from` —— 批量同步：从某一笔起到最新

```bash
python3 sync_pr.py sync-from <unit> [--push] [--no-gate] [--dry-run]
```

| 参数 | 说明 |
|---|---|
| `<unit>` | 起始单元（**含**），同步到最新；写法同 `sync` |
| `--push` | **仅在 full 门禁通过后**统一推送（与单笔 sync 的语义不同） |
| `--no-gate` | 跳过全部门禁（仅调试） |
| `--dry-run` | 只列出批量计划与门禁计划，不执行 |

门禁策略（按需求约定）：

```
单元1 → quick → commit ─┬→ 单元2 → quick → commit ─┬→ … → 最后一笔 → quick → commit
                                                                   ↓
                                                        FULL 门禁（全量构建，一次）
                                                                   ↓
                                                        通过 → [--push 统一推送]
```

行为要点：

- **按 A 时间序逐笔执行**，每笔照常走 apply → quick 门禁 → commit；
- **中途失败即中止**：后序单元可能依赖前序（方案 §4.4 禁止跳跃同步）；已同步单元经台账
  自动跳过，**修复后重跑同一命令即可续传**；
- full 门禁在**最后一笔 commit 之后统一跑一次**；失败则代码已 commit 但未 push，
  台账记 `batch:<起>..<止>` 条目（`full_gate_pass` / `full_gate_failed`），修复后重跑验证；
- 无新同步单元（全部已同步）时跳过 full，直接进入 push/提示环节。

示例：

```bash
python3 sync_pr.py sync-from PR#57 --dry-run   # 先预览批量与门禁计划
python3 sync_pr.py sync-from PR#57             # 执行（只 commit）
python3 sync_pr.py sync-from PR#57 --push      # 执行 + full 通过后统一推送
```

### 3.4 `auto` / `sync_auto.sh` —— 一键式：按同步节点自动同步

```bash
./sync_auto.sh --init <unit>     # 首次：声明"已同步到该单元"（含），初始化 cursor
./sync_auto.sh                   # 日常：同步 cursor 之后的所有单元（一键）
./sync_auto.sh --push            # 同上，full 门禁通过后统一推送
./sync_auto.sh --no-gate         # 跳过全部门禁（quick+full）；台账记 gates_skipped 留痕
./sync_auto.sh --dry-run         # 只看计划（纯本地读取，不 fetch 不执行）
```

**同步节点（cursor）**：持久化在 `sync_state.json` 顶层 `"cursor"` 字段，记录最后一个已处理
单元的 A 侧 commit。语义 = "已同步到该单元（含）"。

每次执行流程：

```
自动更新仓库（A: fetch+master 快进；B: fetch+r2.8 快进；仅 --ff-only，分叉即中止）
→ 扫描单元 → 取 cursor 之后的单元
   ├─ 无 → "✅ 已是最新"，exit 0
   └─ 有 → run_batch（每笔 apply+quick+commit → 最后一笔后统一 full → [--push]）
            每个单元处理成功（含跳过/已同步）即推进 cursor 并落盘
            失败则停在 cursor 处（不推进），修复后重跑同一命令即续
```

行为细则：

- **cursor 推进时机**：单元处理成功才推进（synced / already / skipped / maint_skip 都算
  "已处理"）；失败单元及之后的单元不推进；
- **fetch 失败降级**：离线时告警并继续用本地状态（台账幂等保证安全）；快进失败
  （本地与远端分叉）则中止，需人工处理；
- **cursor 对不上**（A 历史变动导致 commit 不在扫描结果）→ 中止并提示重新 `--init` 对位；
- 手工 `sync` 单笔同步**不会**推进 cursor（保持显式）；auto 运行时会经台账跳过已同步单元
  并顺带推进 cursor；
- 挂定时任务示例：`0 8 * * * cd /root/AI/ms_gitcode/ms-sync-bot && ./sync_auto.sh >> report/auto.log 2>&1`

`auto` 也可直接调 python：`python3 sync_pr.py auto [--init <unit>] [--push] [--dry-run]`。

### 3.5 `replay` —— 离线重放对账（不碰 B 工作区）

```bash
python3 sync_pr.py replay --commit <A侧hash> [--b-base <B侧base>] [--compare <B侧目标>] [--keep]
```

| 参数 | 说明 |
|---|---|
| `--commit` | A 仓单元提交（必填） |
| `--b-base` | 重放的 B 起点提交；缺省用 B 当前 HEAD |
| `--compare` | 对账目标提交（通常是 B 侧人工作业结果）；缺省只打印相对 base 的变更统计 |
| `--keep` | 保留重放 worktree（`report/wt-<id>/`）供检查；缺省用完即删 |

示例（与 08-21 手工同步对答案）：

```bash
python3 sync_pr.py replay --commit 286084f --b-base f1769d12 --compare 2427d50a
```

输出 `工具结果 vs 人工结果` 的 diff 统计，完全一致则打印"（完全一致）"，明细写入
`report/<id>.replay.md`，并在台账记 `replay:<id>` 条目。

### 3.6 `status` —— 查看台账

```bash
python3 sync_pr.py status
```

```
PR#57                 synced        b=1a2b3c4d5e6f mapped=12 ignored=0 generated=0
legacy@286084f868ff   apply_conflict b=- conflicts=[mindspore-lite/CMakeLists.txt]
```

### 3.7 独立调试命令

```bash
python3 path_map.py                        # 映射规则自测（11 个用例）
python3 commit_watcher.py <A仓路径>        # 直接看扫描结果
bash gate.sh quick <B仓路径>               # 门禁：工作区未提交变更
bash gate.sh quick <B仓路径> <base提交>    # 门禁：base..HEAD + 工作区（补验已 commit 的同步）
bash gate.sh full  <B仓路径>               # 全量构建（30min+）
```

---

## 4. 典型工作流

### 日常同步（A 侧按 PR 拆分后）

**一键式（推荐）**——首次初始化后，日常只需一条命令：

```bash
# 首次：声明已同步到哪个单元（含），建立 cursor
./sync_auto.sh --init legacy@286084f868ff    # 或 PR#<N> / hash 前缀

# 日常：自动更新 A/B 仓 → 同步 cursor 之后所有单元（quick 逐笔 + full 收尾）
./sync_auto.sh                                # 只 commit
./sync_auto.sh --push                         # full 通过后统一推送
./sync_auto.sh --dry-run                      # 先看计划
# 可挂 cron：0 8 * * * cd <工具目录> && ./sync_auto.sh >> report/auto.log 2>&1
```

**手动形态**（需要精确控制范围时）：

```bash
# 1. 更新 A、B 本地仓
git -C <A仓> pull --ff-only && git -C <B仓> checkout r2.8 && git -C <B仓> pull --ff-only

# 2. 看有哪些新单元
python3 sync_pr.py list

# 3. 批量同步：从第一笔未同步单元起，逐笔 quick 门禁，最后统一 full
python3 sync_pr.py sync-from PR#57 --dry-run    # 预览计划
python3 sync_pr.py sync-from PR#57               # 执行（每笔 commit，最后 full）
# 单笔补漏/重放：
python3 sync_pr.py sync PR#58

# 4. 确认后推送（sync-from --push 则在 full 通过后自动推）
git -C <B仓> push origin r2.8
```

### apply 冲突 → 人工复核

1. 看 `report/<id>.conflict.md`：冲突文件清单；带 `🛡 protected` 的是 20 个环境适配文件
   （内网镜像/本地依赖探测类改动通常**应跳过**，不逐字移植；功能性注册类改动手工落到 B 版本）
2. B 工作区现场已保留（补丁半应用或未应用状态），手工完成适配
3. 手工 commit（message 只写该 PR 的 description 部分，如 `[Hisilicon_sh] Fix xxx bug`）
4. 台账补录：
   ```bash
   python3 -c "import sync_pr as s; l=s.load_ledger(); \
     s.record(l,'PR#57',status='synced',b_commit='实际commit-hash',note='手工适配')"
   ```

### 里程碑：fork r2.8 → 上游 PR

```bash
# 先与上游对齐（方案 §4.6，否则 PR diff 混入历史差异）
git -C <B仓> remote add upstream git@gitcode.com:HiSpark/mindspore-lite.git   # 首次
git -C <B仓> fetch upstream r2.8 && git -C <B仓> merge upstream/r2.8
# 在 GitCode 页面从 ccc132/mindspore-lite_1815 的 r2.8 向 HiSpark/mindspore-lite 的 r2.8 发起 PR
```

---

## 5. 配置说明

### 5.1 `config.json`

| 字段 | 类型 | 说明 |
|---|---|---|
| `repo_a` | str | A 仓**本地克隆路径**（工具不直接访问远端，先 pull 再跑） |
| `repo_b` | str | B 仓本地克隆路径（同步在这里执行） |
| `a_remote_ref` | str | 预留：A 远端跟踪引用（当前扫描用本地 master） |
| `b_branch` | str | 同步目标分支，sync 前会校验 B 当前分支与之相符 |
| `b_push_remote` | str | `--push` 时的远端名（默认 origin） |
| `fork_pr` | bool | 预留 P2：`true` 时走"单元分支 + fork 内 PR + API 合入"形态（未实现） |
| `gate.default_mode` | str | 门禁档位（当前 sync 固定调 quick，此字段供后续分档调度） |
| `gate.lint_filters` | obj | 预留：lint 规则文件路径覆写（当前固定读 B 仓 `.jenkins/check/config/`） |

### 5.2 `path_map.py` 内置规则（改动需同步更新自测用例）

| 规则 | 当前值 | 效果 |
|---|---|---|
| 同步范围 | 前缀 `src/mindspore-lite/` | 范围外（adaptor/samples/patch/docs 等）全部不同步 |
| 排除目录 | `src/adaptor/`、`src/samples/`、`patch/`、`docs/` | C 部分与无关内容 |
| 映射算法 | 去前缀 + **折叠连续重复段**（`a/a/`→`a/`） | A 的 `src/mindspore-lite/mindspore-lite/tools/tools/x` → B 的 `mindspore-lite/tools/x` |
| 永久忽略 | `cmake/external_libs/opencl.cmake`、`cmake/external_libs/openssl copy.cmake` | §8.3：A 侧历史残留/垃圾副本 |
| 生成物 | `*_generated.h/cc`、`*.gen.h/cc` | 不同步，B 侧构建时重新生成 |

### 5.3 `protected_files.yaml`

| 键 | 用途 |
|---|---|
| `protected`（20 项） | 环境适配文件清单；**不拦截同步**，仅在冲突报告中标注 `🛡 protected`，提示复核者这类差异多为内网镜像/本地依赖探测，通常跳过移植 |
| `ignore_forever`（2 项） | 文档性记录（实际过滤在 path_map.py 的 IGNORE_RULES，两处需保持一致） |

### 5.4 `sync_state.json` 台账（自动维护）

结构：`{"units": {<单元ID>: {...}}, "cursor": {...}}`，单元 ID 三种形态：`PR#<N>` / `legacy@<hash前缀>` /
`replay:<单元ID>` / `batch:<起>..<止>`。字段：`status`（synced/skipped/apply_conflict/gate_failed/
full_gate_pass/full_gate_failed/noop）、`a_commit`、`b_commit`、`mapped/ignored/generated`（文件数）、
`conflicts`（冲突文件列表）、`units`（批量条目的成员）、`note`、`updated_at`。

顶层 `"cursor"` 为一键同步节点：`{"a_commit": <A侧commit>, "unit": <单元ID>}`，语义"已同步到该
单元（含）"；由 `auto --init` 初始化、`auto` 运行时逐单元推进。

---

## 6. A 侧提交信息格式与 B 侧描述策略

### 6.1 A 侧正式格式（2026-09-04 起，实测适配）

```
[CodeHub MR !310] Description: [Hisilicon_sh] Round Gemm Online Weight

（body：revert 相关元数据等，忽略）
Match-id-f756c658ef6d444e36e7a28b9bffada8a70b5121
```

- 识别正则：`^\[CodeHub MR !(\d+)\]\s*Description:\s*(.+)$`，单元 ID = `PR#<N>`（N 为 CodeHub MR 号）
- body 只解析 `Match-id`（兼容 `Match-id-<hash>` 旧式连写），其余忽略
- 兼容保留旧格式：`Repo Sync PR#<N>: <标题>` / `Repo Sync MAINT:` / `HiSpark.AI … Repo Sync <日期>`（legacy）

**同 MR 重复去重**：历史 revert 循环导致同一 MR 出现多次（应用→revert→重应用，中间笔实为
revert 反向 diff）。工具按 MR 号**只保留最后一笔**（净内容），其余告警丢弃。后续无 revert
则不触发。

### 6.2 B 侧 commit 描述策略（2026-09-04 定稿）

**只保留每笔同步 PR 的 description 部分**：

```
A 侧: [CodeHub MR !311] Description: [Hisilicon_sh] Fix Conv3x3 Multi Batch Int8 bug
B 侧: [Hisilicon_sh] Fix Conv3x3 Multi Batch Int8 bug
```

不带 `[CodeHub MR !N]` 前缀、不带 body 元数据。**追溯信息（A 侧 hash / MR 号 / B 侧 commit
对应关系）只存台账** `sync_state.json`，git log 层面不再体现——需要 git 内追溯时查台账或改回
带 trailer 的模板（改 `b_commit_message` 即可）。legacy 单元保持 `sync legacy@…: …` 旧格式。

---

## 7. 状态与待办

| 模块 | 状态 | 说明 |
|---|---|---|
| `path_map.py` | ✅ 完成 | 自测通过 |
| `commit_watcher.py` | ✅ 完成 | 全历史扫描（Repo Sync 在侧支，first-parent 扫不到），legacy 单元识别 + 格式走样告警 |
| `sync_pr.py` | ✅ 完成 | list/sync/sync-from（批量+分档门禁）/**auto（一键+cursor 节点）**/replay/status；`Repo Sync PR#` 检测已实现，等 A 侧切换出真实数据 |
| `sync_auto.sh` | ✅ 完成 | 一键式外壳；auto 的仓库自动更新/fetch 降级/cursor 推进路径需实测（dry-run/初始化/对不上告警已测） |
| `gate.sh` | ✅ 脚手架 | quick 档 lint 生效；抑制规则解析是近似实现（按后缀匹配），必要时再精化 |
| fork 内 PR / API | ⛮ 未实现 | P2/P3（`fork_pr: on` 形态），默认形态不需要 |
| fixup squash | ⛮ 未实现 | 等 A 侧出现 `PR#N fixup` 提交后补 |
| **正式验收** | ⏳ 待实测 | 等 A 仓按 PR 拆分同步后，用真实新单元跑 `sync` 全流程；`replay` 随时可做离线对账 |

## 8. 已知限制（P1）

- 补丁重写对**含引号/非 ASCII 文件名**未做完整 C-style unquote 处理（当前同步范围无此类文件）
- `classify_conflicts` 从 git 报错正则提取冲突文件，个别报错形态可能漏提取（报告仍含完整原始输出）
- 门禁 quick 档的 `.jenkins` 抑制规则按路径后缀近似匹配，与平台 CI 的精确行为可能有细微出入
- `sync` 不自动 fetch/pull A、B 仓（刻意保持显式，避免工具隐式改仓库状态）
