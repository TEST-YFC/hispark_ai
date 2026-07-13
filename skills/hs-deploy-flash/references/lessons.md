# hs-deploy-flash 实证

## 事故 #1: WSL 路径直接传给 flash_server

**症状**：flash_server 返回 "file not found"，但 WSL 里文件存在。

**原因**：flash_server 在 Windows 下运行，不认识 Linux 路径 `/mnt/d/...`。

**修复**：所有传给 flash_server 的路径必须先转为 `D:\...` 格式。

**规则**：红线 4 — WSL 路径必须转 Windows 格式。

---

## 事故 #2: 烧录波特率与串口波特率混淆

**症状**：烧录 `status: success`，但 `monitor_output` 全是乱码。

**原因**：Burntool 烧录用 921600 波特率，但芯片启动后串口打印用 115200。读串口时用了烧录的波特率。

**修复**：flash_server 的 `/flash/burntool` 内建串口监测已正确使用 115200 波特率。

---

## 事故 #3: 编译检查是纯文本无机械执行

**症状**：用户没跑编译直接说"烧录"，skill 跳过检查进了烧录流程。

**原因**：step0 用 prose 写"先决条件"，模型读到有 `curl` 命令的 step1 就跳过去了。

**修复**：增加 `check_prerequisites.sh` 机械闸门，`PREREQ_GATE=PASS` 才继续。

**规则**：红线 1 — 编译未完成不烧录，闸门脚本强制执行。
