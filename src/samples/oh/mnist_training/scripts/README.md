# 脚本

`preproc_mnist_data.py` 用于下载 MNIST 数据集，并导出归一化后的 `float32` 图像数据。
训练集 BIN 数据用于 converter 量化校准，测试集数据可用于板端验证和评估。

请在 `samples/oh/mnist_training` 目录下执行：

```bash
python scripts/preproc_mnist_data.py \
  --orig_path ./data \
  --train_path ./data/train_data \
  --test_path ./data/test_data \
  --train_file_format bin \
  --test_file_format all \
  --test_data_type float32 \
  --train_count 50
```

训练集 BIN 数据在 `model/micro_train.cfg` 中的使用方式如下：

```ini
calibrate_path=input:data/train_data/bin
```

默认只导出 50 个训练样本，与 `model/micro_train.cfg` 中的 `calibrate_size=50` 保持一致。
