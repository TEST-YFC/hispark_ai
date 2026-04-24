# 1. ONNX LeNet-5 分类网络模型量化

## 1.1 量化前提
本用例使用LeNet-5模型，存放于目录../../../oh/lenet5/model/mnist-12.onnx

## 1.2 量化示例
请在当前目录执行如下命令运行示例程序：
```none
bash ./scripts/run_calibration.sh
```
> 网络问题导致下载出现问题，可以手动创建./data/MNIST/raw文件夹（./data目录对应数据处理脚本preproc_mnist_data.py的入参--orig_path），并下载数据包 [train-images-idx3-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/train-images-idx3-ubyte.gz)、[train-labels-idx1-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/train-labels-idx1-ubyte.gz)、[t10k-images-idx3-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/t10k-images-idx3-ubyte.gz)、[t10k-labels-idx1-ubyte.gz](https://ossci-datasets.s3.amazonaws.com/mnist/t10k-labels-idx1-ubyte.gz)到raw下，再执行脚本。

## 1.2 量化结果
量化成功后，在当前目录会生成量化日志文件 ./amct_log/amct_onnx.log ，并在当前目录下生成以下内容：

+ output: 存放量化后模型的文件夹。
  + mnist_deploy_model.onnx: 量化部署模型，即量化后的可在昇腾 AI 处理器部署的模型文件。
  + mnist_fake_quant_model.onnx: 量化仿真模型，即量化后的可在 ONNX 执行框架 ONNX Runtime 进行精度仿真的模型文件。
  + mnist_quant.json：融合信息文件。

量化仿真模型的精度如下表：
| 模型 | Accuracy |
| :--: | :-: |
| 原始Float32模型 | 98.80% |
| 量化Int8模型 | 98.91% |