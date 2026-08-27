import onnx
import onnx.shape_inference
from onnx import helper
def create_low_ir_version_model(graph_def, producer_name, output_path, ir_version=10, opset_version=22, infer_value_info=False):
    """创建指定IR版本的模型

    infer_value_info=True时对模型做shape推断并把中间张量的静态shape写入
    value_info, converter解析时可直接取用而无需依赖自身对算子(如TopK)
    的形状重新推断; 仅保留完全静态的条目, 含符号维(动态长度)的一律丢弃
    """
    # 创建模型时指定较低的IR版本
    model_def = helper.make_model(
        graph_def,
        producer_name=producer_name,
        ir_version=ir_version,  # 使用较低的IR版本
        opset_imports=[helper.make_opsetid("", opset_version)]  # 指定操作集版本
    )
    if infer_value_info:
        model_def = onnx.shape_inference.infer_shapes(model_def)
        static_vi = []
        for v in model_def.graph.value_info:
            dims = v.type.tensor_type.shape.dim
            if dims and all(d.HasField('dim_value') for d in dims):
                static_vi.append(v)
        del model_def.graph.value_info[:]
        model_def.graph.value_info.extend(static_vi)

    # 保存模型
    onnx.save(model_def, output_path)
    return model_def