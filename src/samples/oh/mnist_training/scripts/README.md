# 脚本

`preproc_mnist_data.py` 用于下载 MNIST 数据集，并生成 converter 量化校准数据和 MCU sample 内置训练/评估数据。

请在 `samples/oh/mnist_training` 目录下执行：

```bash
python scripts/preproc_mnist_data.py \
  --orig_path ./data \
  --calib_path ./data/calib_data
```

校准集 BIN 数据在 `model/micro_train.cfg` 中作为 converter 量化校准数据：

```ini
calibrate_path=input:data/calib_data/bin
```

默认只导出 500 个校准样本，与 `model/micro_train.cfg` 中的 `calibrate_size=500` 保持一致。

同时会生成 MCU sample 内置数据：

```text
src/mnist_training_data.c
```

生成策略：

```text
训练集：500 张，每类 50 张，uint8 存储
评估集：500 张，uint8 存储
```

板端运行时会将 `uint8` 图像逐张转换为模型输入需要的 `float32 / 255.0`。
