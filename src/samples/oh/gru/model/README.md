# Gru model applied on Google Open-speech Dataset

## 模型介绍 && 下载链接
[supported]: https://img.shields.io/badge/-supported-green "supported"
[no support]: https://img.shields.io/badge/-no_support-red "no support"
| Model    | Chip List              | Params (KB)  | Flops (kMacs) |
|----------|------------------------|---------|-------|
| GRU_S    | Hi3863, Hi3322 ![alt text][supported]  | 78.09 | 100.852 |

## 模型性能
| name | Chip | Quant Cfg | Platform | Flash(KB) | RAM(KB) | Latency(ms) | Accuracy(%) |
|----------|------------------------|---------|-------|-----|-----|----|---|
| GRU_S | Hi3863 | No | RISC-V | 325.69 | 15.94 | 115 | 91.79 |
| GRU_S | Hi3863 | No | RISC-V | 105.87 | 15.83 | 96 | 80.97 |

Tip: 此数据Stack基于Sample静态配置(12KB)

## License
