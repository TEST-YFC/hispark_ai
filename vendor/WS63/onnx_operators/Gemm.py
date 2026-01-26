# Copyright (c) HiSilicon (Shanghai) Technologies Co., Ltd. 2025-2025. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
from onnx import helper, TensorProto
from . import create_low_ir_version_model

def create_gemm_onnx_model(output_path, alpha=1.0, beta=0.0, transA=0, transB=0, M=3, K=4, N=2):
    """创建GEMM算子ONNX模型"""
    print(f"创建GEMM模型: {output_path}")
    
    input_A = helper.make_tensor_value_info('A', TensorProto.FLOAT, [M, K])
    input_B = helper.make_tensor_value_info('B', TensorProto.FLOAT, [K, N])
    output_Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [M, N])
    
    gemm_node = helper.make_node(
        'Gemm',
        inputs=['A', 'B'],
        outputs=['Y'],
        alpha=alpha,
        beta=beta,
        transA=transA,
        transB=transB,
        name='gemm_node'
    )
    
    graph = helper.make_graph(
        [gemm_node],
        'gemm_graph',
        [input_A, input_B],
        [output_Y]
    )

    model = create_low_ir_version_model(graph, producer_name='gemm-generator', output_path=output_path)
    print(f"✓ GEMM模型已保存: {output_path}")