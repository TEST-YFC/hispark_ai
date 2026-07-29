# 历史事故教训（按症状索引）

本文承接 SKILL.md 正文撤下的全部"实证"事故：每条 = 症状 → 根因 → 规则。**用法：卡住、报错、或想走捷径时，先按当前阶段在这里查症状**；命中就照"规则"列执行，不要重新发明绕过方案——下面每条都是某次会话真实烧掉数小时后总结的。

## 决策期（step1-step3）

| 症状 / 想做的事 | 真实事故 | 规则 |
|---|---|---|
| scan 输出太长，想 `head`/`tail` 截断 | `tail -60` 恰好截掉 decision1 的 ONNX 语义摘要段，模型拿幸存的另一框架同名摘要误判 decision2 候选语义，错走新建分支 | scan 输出必须完整读；过长从 `/tmp/scan_op_<Op>.log` 读全文 |
| 拿"与候选同名的其它框架算子"的摘要判语义 | 同一算子名在 ONNX 是三输入 numpy 广播选择、在 TFLite 是返回 true 坐标的单输入算子；拿后者裁决前者得出"语义完全不同"，错走新建 | 候选语义真值 = 仓内 ④infer + ⑤kernel 源码，Read 后裁决；同名异义是常态 |
| 同族两个 builtin 看着差不多，想共用 parser | TFLite 把无广播的 `SelectV2` 调用规范化成 `SELECT`，真广播形状才发 `SELECT_V2`——两者语义不同、输入域不同 | 广播版/非广播版 = 两个独立算子；同形输入收敛到非广播版（优先保证其链路完整）；形状→builtin 映射用可达性探针实证，不凭 raw_op 名推断 |
| 语义摘要里有 `SameOperandsAndResultsScale`，想据此让 int8 跳过重量化 | 该 trait 是源框架自家 runtime 的约定；MSLite 全量化器给每个张量独立分配 scale/zp，不落实同 scale 约束。以 trait 为据省重量化，只在量化器恰好分配相同 qparams 的用例上侥幸通过，判别用例下即暴露 | int8 通路一律按 ⑤‴ 模板逐输入重量化（qparams 相同时自动退化为拷贝，永远正确） |
| 链路表 ⑤ 有文件就标「已有」 | 存量 kernel 仅 fp32：FULL_QUANT 的 bias_correction 在宿主运行时执行 int8 模型，缺口拖到 int8 转换才以堆越界/卡死现身，排查代价最高 | 看 scan ⑤′ 段；无 int8 处理标「已有(仅fp32)」并把 int8 分支列入缺失 |
| 复用分支想"只补三层就完" | 存量广播 kernel 跨维广播算错、同 rank 广播被拒、int8 数据被按 fp32 写入致堆越界——全部到 hs-debug-op-host-accuracy 才暴露 | 「已有」≠「已验证」；呈现复用方案时讲明存量层可能要修；FAIL 定位到存量代码也在本次范围内 |
| 拿"既有 parser 已这样映射"当 decision2 复用依据 | 既有映射正是上一轮缺陷实现留下的，循环论证 → 超集 builtin 被并入子集 PrimType，且重复实现了仓内已有的广播设施 | 既有映射是审查对象不是裁决依据；四条判据独立裁决，冲突写进 decision4、改造既有代码 |
| 探针表只填"验证方法"列就当作做过探针 | step3 呈现了一张断言"两 builtin 各自独立可达、不存在归一化"的探针表，实际没跑任何解包命令——实测同形 SelectV2 被 converter 归一化成 SELECT，第一版用例整轮全测错算子 | 探针表每行必须附本会话解包命令的实际输出；"不存在归一化"恰是探针要证明的命题，不得以该断言豁免探针 |
| 链路/能力清单标「已有」只看文件存在 | 某 optimizer pass 文件存在但只挂在 GE 流程，CPU converter 根本不跑它——能力被标"✅ 已有"，缺口拖到 step7 验证才暴露 | 「已有」须给定义点 + 注册/可达点两处证据；未注册进本目标路径 = 不可达，按缺失计 |
| 想现写 python 内省 `onnx.defs` 查 opset/属性差异 | OpSchema 字段名靠猜（`.name`/`.num_inputs` 全不存在），连续 4 次 AttributeError 才拿到属性表，纯无谓消耗 | opset/属性规格只经 `fetch_op_spec.py --op <Op>`（scan 已内调）或 spec-sources.md 给定的单行命令**照抄执行**；禁止现场手写内省脚本 |

## 实现期（step4）

| 症状 / 想做的事 | 真实事故 | 规则 |
|---|---|---|
| 凭印象先写完，再用指南"纠错" | 构造函数签名、serializer 类名、目录归属、int8 量化接口起笔写错，返工是整文件级而非局部修补 | 动笔前打开实现指南对应小节，以模板为底稿改名填空 |
| 校验宏按 `assert(条件成立)` 直觉使用 | `CHECK_LESS_RETURN(axis, dims_size)` 想表达"校验 axis<dims_size 合法"，实际宏语义是「第一参 < 第二参即报错返回」——全部合法 axis 被误杀，INT8 整轮 FAIL，烧一轮构建+验证才定位。同文件另一处 `CHECK_LESS_RETURN(in_tensors_.size(), C1NUM)` 用法正确——按片段模仿而非按语义使用正是事故根源 | mslite 校验宏读作「**保证**」不读作「断言」：`CHECK_LESS_RETURN(a,b)` 保证 a≥b（a<b 时报错返回），**只能表达下界**；上界条件（合法 = `a < b`，如 `axis < dims_size`）**禁止用该宏族表达**——必须写显式 `if (a < 0 \|\| a >= b) { MS_LOG(ERROR) << ...; return RET_ERROR; }`（实测连规则在手的模型也会把 `CHECK_LESS_RETURN(axis, dims_size)` 误当上界检查）。用任何 `CHECK_*_RETURN` 前先读其定义（`nnacl_c/op_base.h` / `src/common/`） |
| int8 函数签名不带量化参数（字节拷贝） | 字节拷贝在输入/输出 scale 不同的场景下以 ~0.99 假绿混过阈值多次 | ⑤‴：签名必须带各输入/输出 scale/zp 并逐输入重量化 |
| 用定点乘数（`QuantizeMultiplierSmallerThanOne`）替代 float-ratio | 定点乘数对 ratio=1.0 产生的不是恒等变换，在输入/输出 scale 相同的常见用例上制造系统性偏差；后续为它补"scale 相等跳过"特判 = 在错误方案上叠补丁 | 重量化用 ⑤‴ 的 `float ratio + lrintf`，对任意 scale 比值正确 |
| condition/index 首输入算子按常规建 fp32+int8 成对 coder | 运行时与 codegen 都按 `inputs[0]->data_type()`（bool/int）派发——按 `kNumberTypeInt8` 单独注册的 kernel 是永不被选中的死代码，bias_correction 阶段堆越界 | decision3 开关 ④ 必须在创建任何 ⑤/⑥ 文件前定下：单注册键 + 内部按数据张量 dtype 分支（⑤″） |
| int8 运行时 LiteKernel 把 shape/`n_dim_`/axis 派生态只放在 `ReSize()` | converter 的 bias_correction 子流程不保证 `ReSize()` 先于首个 `Run()`——`n_dim_=0`，int8 全路转换 FAIL，烧一轮构建+验证才定位（实证 Hardmax）；模型抄参考 kernel 时最易丢掉这一句 | `Prepare()` 必须建立 `Run()` 所需全部派生态并以 `return ReSize();` 收尾（本仓 53 个 int8 kernel 中 42 个如此，是框架契约非个别风格）；`ReSize()` 按当前 shape 重算派生态。**这是骨架/数值分离的反例：该抄的契约丢了，不该抄的数值反倒可能被带进来——参考算子按结构族选、只抄结构不抄数值** |
| 给已有 PrimType 加同键第二注册 | `REG_KERNEL` 注册表先于 nnacl 注册表被查询，同键再注册会整体劫持既有 kernel 连同其已验证的广播/快路逻辑 | 扩展留在既有体系内：C++ LiteKernel 加 dtype 分支；nnacl KernelBase 扩 struct + shim 填 qparams（⑤″ 第 7 条）；grep 确认每 dtype 键注册唯一 |
| 新加 int8 分支只覆盖主路径 | 单元素条件走 `MoveData` 字节搬运，quantized 数据从旧快路漏过——单元素输出余弦恒 1.0，行为验证测不出 | 改造存量 kernel 必做全执行路径审计：枚举每条输出写入路径（dtype 分支/单元素快路/memcpy/in-place/早退），逐条确认 int8 经重量化或不可达 |
| 放开存量 kernel 的入口守卫，却没修被放开的路径 | 删掉过严的广播形状检查后，从未被验证的存量广播路径暴露出来且算错——把"功能缺失（显式报错）"变成了"静默算错"，比改之前更危险 | 放开守卫与修通路径是同一件事的两半：放开前先验证（或修好）守卫背后的路径；验证不过就连守卫一起还原，不留半成品 |
| 手写广播索引 | `i % num` 仅最外维广播碰巧正确；stride 公式漏乘 `shape[d+1]`；"任一输入是标量"式存在性守卫放过混合形态 | 按实现指南 ⑤⁗：优先复用 nnacl 既有广播设施；快路守卫对每个输入逐一成立 |
| 能力清单列了，对应代码"回头再写" | 清单明列 rank-1 条件模式与 int8 广播「需新增」，代码从未落地，直到验证才暴露 | 每层完成立即回填落点 `文件:函数`；启动编译前清单上不得有无落点的「需新增」能力 |
| 各层 rank 上限常量都对上了，就认为越界已防住 | Hardmax 各层数组/守卫都是 `DIMENSION_4D`（"同常量"判据满足），但 infer 用 `SetShapeTensor` 同形传播**无 rank 守卫**、nnacl fp32 kernel `input_shape_[DIMENSION_4D]` 在 `InitHardmaxParam` 里 `for i<n_dim` 直写**填充前无守卫**——5D 模型 infer 放行、fp32 校准期数组越界；用例全 ≤4D 跑出 48/48 全绿，缺陷完全不可见 | rank 上界是**两条独立判据**：① 同常量；② infer 显式拒绝超界 + 每个 `[DIMENSION_*]` 数组填充循环前有守卫。① 满足不蕴含 ②——"同常量"过了仍要单独查"infer 设闸 + 数组填充前守卫"。`quick_check.sh` rank advisory (2)/(3) 已秒级拦此型，命中即缺陷，不得因 ≤上限用例全绿放行 |
| 新建 nnacl_c 头文件漏 `extern "C"` 守卫 | 编译全过、链接期 `undefined reference`，烧一轮 ~7 分钟构建才暴露（C 符号被 C++ 调用方按 mangle 名解析） | 模板起笔即带守卫（实现指南 ⑤‴）；`quick_check.sh` 已对 `nnacl_c/{fp32,int8,fp16,infer,base}/` 的 .h 做秒级 lint |
| 用图层 pass 插 `BroadcastTo`/`Reshape` 节点实现广播 | 两次走该方案（挂存量 pass 进 CPU 列表、新写 pass）：converter 能过，micro codegen 缺被插算子的 coder（尤其 bool dtype），全部用例 ERR，整体回滚，净烧 3 轮构建 + 2 轮验证 | ⑤⁗ 歧路条目：被插算子 × dtype 有 coder + 全局回归面评估，两条查实前不得选图层方案；默认在 kernel/coder 内部处理 |
| condition/index 首输入算子的 runtime kernel 按 `where->data_type_ == kNumberTypeInt8` 分 int8 分支 | 该 struct 的 `data_type_` 装的是**注册派发键 = 首输入（condition）的 dtype = bool**，不是数据张量 dtype；int8 分支恒假成死代码，int8 数据落进 fp32 通路被按 float 重解释 → 4× 字节越界，converter "转换成功"后在 bias_correction 执行该 kernel 时野指针崩溃（被误报成"TF converter 慢"，假结论又误导下一会话） | 首输入是 condition/index 的算子，runtime kernel 内分 fp32/int8 **必须读 `in_[<数据输入下标>]->data_type_`**（如 Where 读 `in_[Index1]`），不是 struct 的 `data_type_` 字段；`quick_check.sh` 的 dtype-dispatch advisory 已对"bool 注册键 + `data_type_==kNumberTypeInt8`"组合秒级告警。**转换期崩溃/卡死一律先读 stderr 首行定位层（parser/quant/bias_correction/codegen），禁止归因环境慢**——一条 int8 用例在校准期即可秒级复现 |

## 构建期（step5-step6）

| 症状 / 想做的事 | 真实事故 | 规则 |
|---|---|---|
| 跳过预检直接构建 | narrowing/未声明变量这类秒级可查的语法错误，烧了 3 轮 10–30 分钟构建才清完 | `quick_check.sh` FAIL 清零才许启动构建 |
| 构建失败后改手敲 `export MSLITE_*` + 裸跑 `build.sh` | env 全丢、产物配置错误，连续多轮 20 分钟构建作废后才发现 | 重跑也只经 `build_mslite.sh` |
| `wait <PID>` 判断构建完成 | 每次 Bash 工具调用是新 shell，构建进程不是其子进程，`wait` 必返 127；把 127 误读为构建退出码 → 状态误判 → 并发构建互踩 → pkill 清场 | 只用 `--status` 判进度 |
| 用长 `sleep`（300/600s）等构建，或自拼 `sleep N && --status` 链 | 单次 sleep 被 Bash 工具默认 120s 超时杀掉（exit 143/144），连续多条全被杀，白耗轮次还制造假错误信号；调高工具 timeout 绕开规则后又把被杀的 sleep 误读为构建结果 | 用 `build_mslite.sh --wait 540`（Bash 工具 timeout 600000）阻塞等待，到时返回 10 就再 `--wait`；--status 仅即时查看，轮询时单次 sleep ≤110s |
| 构建期间顺手改源码 | 中途改的文件不进本轮产物，得到"改完了但测的是旧码"的假状态 | 要改代码先 `--stop`（清整个进程组；裸 `kill` 留孤儿 make 互踩，`pkill -9 -f make` 误杀无关进程） |
| 链接失败就清缓存/删 build 碰运气 | 盲目逐级清缓存连烧 4 轮构建约 1.5 小时仍未定位根因 | 先拿到 undefined 符号名与失败 target（`--status` 链接专项），读该 target 的 CMakeLists 看源收集方式、`nm` 核实符号归属，再动手 |
| 编译报错文件不是本会话改的，顺手修掉 | 改了子模块内无关文件换编译通过，污染范围 | 对照本会话文件清单（`git status` 佐证）；预存问题停下报告用户裁决 |
| 重写报错文件时"简化实现" | coder 首版编译报错，重写时把广播分支整段删掉——编译变绿，缺口拖到 hs-debug-op-host-accuracy 才暴露，且仅因用例恰好覆盖才被发现 | 修编译错误只许最小改动；重写后立即对照能力清单核对每条能力代码仍在 |
| 工具链没搜到，上报"不存在"或退化 x86-only | 搜索命令被权限拒绝 / `-type f` 漏符号链接，得出假结论；x86-only 不产出交叉库，等于没验证 | 命令被拒或无果 = 未知不是否定证据；脚本报"未找到"的唯一动作 = 停下向用户要路径 |
| `--status` 报 RUNNING 但日志尾部是上一轮的 BUILD OK，于是 `--stop`"清场" | 调用方把日志重定向到自定义文件，`--status` tail 的固定路径里残留上一轮内容——杀掉的是健康构建，多烧一轮 | 启动命令不自行重定向（脚本自管日志并截断旧内容）；RUNNING 行附"已运行时长"，时长在涨 = 真在跑，与日志尾部矛盾时信 RUNNING |
| 新建 `nnacl_c/{base,fp32,int8}/*.c` 后直接增量 build | nnacl_c 的 CMake 用 `file(GLOB ...)` 收集源文件，GLOB 只在 **configure 期**展开；增量 `make` 不重配 → 新 `.c` 静默不参与编译，链接期缺符号、或更糟用到旧对象得假结论 | 新增源文件后先 `touch` 对应目录的 `CMakeLists.txt`（强制 re-glob/重配）再 `build_mslite.sh`；新 `.c` 用 `NNACL_OK/ERR` 记得 `#include "nnacl_c/errorcode.h"`（op_base.h 不含，quick_check 秒级抓） |
| 构建后之前全绿的用例成片 converter 报错 / 报 `gen_lite_ops.h: No such file` / converter 一启动就崩，于是去改算子代码 | `build.sh` 的 `update_submodule` 跑 `git submodule update --init --remote`，把受管 `mindspore` 子模块从基线 commit 静默推进到上游最新（如 `2365375a→0487e01a`）：converter 行为漂移、之前全绿用例成片失败，新 commit 还与已 configure 的 `build/` 不兼容报缺生成头。一次会话误判成算子 bug——先改 INT8/fp32 coder，再 `git checkout` 子模块到不同 commit、`git stash`、改 `build.sh`、反复清 `build/` 重建，越陷越深、数小时无果 | **成片回归先查环境不查算子。** `build_mslite.sh` 已在构建前记录子模块 SHA，漂移即 `[SUBMOD-LOCK] exit 7` 硬停；命中即按提示把子模块 `checkout` 回构建前 SHA、注释 `build.sh` 第一处 `update_submodule` 调用后经本脚本重建（红线 4）。**禁止** `git checkout` 子模块到别的 commit / `git stash` / 反复重建试错；改码前先用一个已知用例确认基线可过 |

## 验证期（step7）

| 症状 / 想做的事 | 真实事故 | 规则 |
|---|---|---|
| 把 FAIL 归因"量化精度固有限制/退化输入无意义" | 被这样合理化掉的 FAIL 后来证实正是实现 bug 的信号（全零/单元素轴暴露哨兵塌缩；多输入不同值域暴露重量化错误） | 任何 FAIL 先定位根因再结案；fp32 全过不能证明选择/归约逻辑对（fp32 哨兵常取 −∞，掩盖同构的 int8 塌缩） |
| 用仓内其它能出余弦数字的流程替代 hs-debug-op-host-accuracy | 厂商基准脚本/样例自带测试的用例未覆盖判别场景（敏感值域、退化输入、输出分布≠输入分布），全绿也排除不了真实缺陷 | 精度验证唯一入口是 hs-debug-op-host-accuracy |
| INT8 余弦恰好 `1.0000` 当 PASS | 量化没真正生效（算子缺 `support_int8_ops_`，tensor 保持 fp32，选了 fp32 coder）——真 INT8 应落 `[0.99, 1.0)` | 恰好 1.0000 默认按 FAIL 查 ⑦ 量化器列表 |
| 自写 `op_spec.py` 的 int8 输入（`linspace+shuffle`／随机），不用模板的 `make_distinct_axis_inputs` | 排序/归约类（Hardmax/ArgMax/TopK 等输出由"谁更大"决定）的算子，大 shape 下同轴相邻元素被量化进同一桶（间隔 < 量化桶宽），argmax 在量化后漂移——**fp32 全过、仅大 4D int8 用例 FAIL**（实证 Hardmax tc6/tc11 首轮 FAIL），易误判成 kernel bug，实为输入设计缺陷；而 `operator_spec_template.py` 早有现成的 `make_distinct_axis_inputs` 解决此事，自写绕开了它 | op_spec **一律从 `operator_spec_template.py` 拷贝改写**（hs-debug-op-host-accuracy「唯一模板」），排序类 int8 用例直接用其 `make_distinct_axis_inputs`（沿轴等距铺开+广播，间距远大于桶宽）；诊断信号「fp32 过、大 shape int8 独 FAIL」先排除输入分桶塌缩再怀疑 kernel。算法依据见 `references/int8-coder-conventions.md §2b` |
| 多算子任务只跑出一行 VERDICT 就宣布全部完成 | converter 按形状归一化 builtin（无广播用例被悄悄发成同族另一 builtin），目标算子可能从未被任何用例命中——"42/42 全绿"也证明不了它 | 逐算子各一行 VERDICT；同族多 builtin 附「形态→builtin」探针证据（解包命令见 decision2-reuse-decision.md） |
| 贴着含 FAIL 的 VERDICT 写"状态: 完成"，理由是"存量缺陷，非本次引入，需后续修复" | 复用分支 = 接管存量质量，FAIL 在被复用 kernel 里同样是本任务的缺陷；"非本次引入"只是根因描述不是结案理由——格式合规（贴了 VERDICT）掩盖了实质造假（VERDICT 是红的） | `状态: 完成` 的判据是机械的：每行 VERDICT 0 FAIL + 退出码 0；做不完就如实写 `状态: 未完成（阻塞: ...）` 向用户求助——停下合法，包装失败不合法 |
| FAIL 后不读现场、连换方案盲试 | 三个修复方案逐一全量构建后失败，每轮只浅层 grep 从未引用 stderr.log 的具体错误行；第三次失败后直接放弃整块能力 | step7 修复循环固定步骤：先贴错误行原文 + 查本表 + 呈现根因，才许动代码；同一能力连续 2 个方案失败 → 强制停下向用户呈报选项 |
| 修不动就删 FAIL 用例重跑，拿 0 FAIL 宣布"完成 + 已知局限" | 广播用例实跑 FAIL 后被从 op_spec 删除，重跑 "36/36 PASS" 当完成上报——能力清单里两行能力静默消失，且"已知局限"包装恰是 SKILL.md 明令禁止的措辞 | VERDICT 的分母是 step3 能力清单不是现存用例；hs-debug-op-host-accuracy 的 CASES_REDUCED 闸门拒跑缩水的用例集，豁免须 `OP_VERIFY_ACK_REDUCED=1` 且经用户裁决、在 VERDICT 留痕 |
| 回填能力清单时把行内容"顺手"改成实际跑的用例值 | step3 计划 `[1,8,32,32] axis=2`、`[4,10,16] axis=1` 两行，回填表被静默改写成实测的 axis=-1 形状——表面"全覆盖"，实际「大 shape × 中间轴」路径无任何用例，且漂移对用户不可见 | 回填只许**追加**落点/用例编号，形状/轴/属性照抄 step3 原文（SKILL.md 完成判据 4）；实测与计划不一致的行标「计划变更（原 X → 现 Y，理由）」呈现给用户裁决；对账存量 op_spec 的方向是改 spec 配清单，不得反向改清单配 spec |
| 结案不做 diff 终审 | 被回滚方案的伴生改动（只挂 GE 流程的 pass 里的死代码、为它加的 include）与拆掉一半的存量入口守卫留在仓里交付——守卫拆一半 = "显式报错"变"静默算错" | 完成检查清单 `git diff` 终审：每个改动文件映射到能力/用例；废案连伴生改动一起还原；放开的守卫要么其路径有 PASS 用例、要么连守卫还原 |
