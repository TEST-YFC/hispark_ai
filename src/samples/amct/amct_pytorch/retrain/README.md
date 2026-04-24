# LeNet-5
## 1. 量化感知训练

### 1.1 量化前提

+ **模型准备**
拷贝原始模型lenet5.pt到model目录下

+ **数据准备**
请在当前目录执行如下命令运行示例程序：
```none
python3 ../../../oh/lenet5/scripts/preproc_mnist_data.py --orig_path ./data --train_path ./train_data --test_path ./test_data --train_file_format npy --test_file_format npy
```
> 网络问题导致下载出现问题，可以手动创建./data/MNIST/raw文件夹（./data目录对应上述命令的入参--orig_path），并下载数据包 [train-images-idx3-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/train-images-idx3-ubyte.gz)、[train-labels-idx1-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/train-labels-idx1-ubyte.gz)、[t10k-images-idx3-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/t10k-images-idx3-ubyte.gz)、[t10k-labels-idx1-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/t10k-labels-idx1-ubyte.gz)到raw下，再执行脚本。


### 1.2 量化示例

执行量化示例前，请先检查当前目录下是否包含以下文件及目录

+ [model](./model)
    + lenet5.pt
+ [src](./src)
    + lenet5_retrain.py
+ test_data
    + npy
    + label.csv
+ train_data
    + npy
    + label.csv

请在当前目录执行以下命令运行示例程序：

```
python3 ./src/lenet5_retrain.py --train_set ./train_data --eval_set ./test_data --model ./model/lenet5.pt --config_defination ./src/retrain_conf/retrain.cfg
```
上述命令只给出了常用的参数，全部参数以及各个参数解释参见如下表格
| 参数 | 必填项 | 数据类型 | 默认值 | 参数解释 |
| :-- | :-: | :-: | :-: | :-- |
| -h | 否 | / | / | 显示帮助信息。 |
| --model MODEL | 是 | string | None | 参数文件路径。 |
| --config_defination CONFIG_DEFINATION | 否 | string | None | 量化的简易配置文件路径。 |
| --batch_num BATCH_NUM | 否 | int | 2 | retrain 量化推理阶段的 batch 数。 |
| --train_set TRAIN_SET | 是 | string | None | 测试数据集路径。 |
| --eval_set EVAL_SET | 是 | string | None | 验证数据集路径。 |
|  --num_parallel_reads NUM_PARALLEL_READS | 否 | int | 4 | 用于读取数据集的线程数，根据硬件运算能力酌情调整。 |
| --batch_size BATCH_SIZE | 否 | int | 25 | PyTorch 执行一次前向推理所使用的样本数量，根据内存或显存大小酌情调整。 |
| --learning_rate LEARNING_RATE | 否 | float | 1e-5 | 学习率。 |
| --train_iter TRAIN_ITER | 否 | int | 2000 | 训练迭代次数。 |
| --print_freq PRINT_FREQ | 否 | int | 10 | 训练及测试信息的打印频率。 |

若出现如下类似信息，则说明量化成功：
```none
2025-12-16 09:47:17 - INFO - [INFO] Accuracy before retrain: 98.900%
2025-12-16 09:47:17 - INFO - [INFO] Accuracy after retrain: 98.930%
```

### 1.3 量化结果

量化成功后，在当前目录会生成量化日志文件 ./amct_log/amct_pytorch.log、./output 和 ./tmp 文件夹，该文件夹内包含以下内容：

+ tmp: 临时文件夹
  + config.json: 量化配置文件，描述了如何对模型中的每一层进行量化。
  + record.txt: 量化因子记录文件记录量化因子。
  + model_best.pth.tar: PyTorch 模型量化感知训练过程中生成的 checkpoint 中间文件。
+ output: 输出文件夹
  + lenet5_deploy_model.onnx: 量化部署模型，即量化后的可在昇腾 AI 处理器部署的模型文件。
  + lenet5_fake_quant_model.onnx: 量化仿真模型，即量化后的可在 ONNX 执行框架 ONNX Runtime 进行精度仿真的模型

> 如果量化脚本所在目录下已经存在量化配置文件，则再次调用 `create_quant_config` 接口时，如果新生成的量化配置文件与已有的文件同名，则会覆盖已有的量化配置文件，否则生成新的量化配置文件。

量化仿真模型的精度如下表：
| 模型 | Accuracy |
| :--: | :-: |
| 原始Float32模型 | 98.80% |
| 量化Int8模型 | 98.93% |
