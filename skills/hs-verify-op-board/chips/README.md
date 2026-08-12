# 芯片扩展目录

每个芯片使用独立目录：

```text
chips/<chip>/
├─ references/   芯片SDK、设备、串口和故障规范
├─ scripts/      该芯片的模型构建、Sample和SDK接入入口
└─ tests/        芯片入口的隔离测试
```

通用的Host GT选择、余弦比较协议和`board_accuracy.py`保留在`hs-verify-op-board`顶层。
新增芯片时不得复制WS63路径后凭经验替换字符串；必须提供对应SDK identity、确定性脚本、
测试以及完整的当前接入规范。
