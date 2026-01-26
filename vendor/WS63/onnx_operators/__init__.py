import onnx
from onnx import helper
def create_low_ir_version_model(graph_def, producer_name, output_path, ir_version=10, opset_version=22):
    """创建指定IR版本的模型"""
    # 创建模型时指定较低的IR版本
    model_def = helper.make_model(
        graph_def,
        producer_name=producer_name,
        ir_version=ir_version,  # 使用较低的IR版本
        opset_imports=[helper.make_opsetid("", opset_version)]  # 指定操作集版本
    )
    
    # 保存模型
    onnx.save(model_def, output_path)
    return model_def