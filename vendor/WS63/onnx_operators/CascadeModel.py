# Copyright (c) 2025-2026 HiSilicon (Shanghai) Technologies Co., Ltd. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 级联算子覆盖用例: Gelu HardSigmoid Celu Erf Trilu ReduceL1 ReduceL2 Shape
# TopK Neg Pow Mod MatmulInteger Max Min Sum OneHot Unique ConvInteger Where
# ReduceProd LogSoftmax Hardmax Softplus Softsign ThresholdedRelu
# 双输出模型: Z[1,131]为主输出(第0个), unique_vals(变长)为第1个输出;
# Unique变长输出按micro coder要求必须终端输出, 不能作为中间张量消费
# MatmulInteger说明: CI镜像ORT未注册该算子kernel, gen_dataset加载时会在
# *_converted.onnx临时副本中将该节点替换为恒等浮点子图以生成参考值, 原始
# .onnx不动, converter_lite转换的仍是原生算子
# (见gen_dataset的_make_matmulinteger_ort_compatible)
import logging
from onnx import helper, TensorProto
import numpy as np
from . import create_low_ir_version_model

logging.basicConfig(level=logging.NOTSET)


def _make_activation_chain_nodes(initializer_list):
    """激活函数级联: Neg -> Pow -> Gelu -> HardSigmoid -> Celu -> Erf ->
    Softplus -> Softsign -> ThresholdedRelu -> Hardmax -> LogSoftmax"""
    pow_exp = helper.make_tensor('pow_exp', TensorProto.FLOAT, [], [2.0])
    initializer_list.append(pow_exp)
    neg_node = helper.make_node(
        'Neg', inputs=['X'], outputs=['neg_out'])
    pow_node = helper.make_node(
        'Pow', inputs=['neg_out', 'pow_exp'], outputs=['pow_out'])
    gelu_node = helper.make_node(
        'Gelu', inputs=['pow_out'], outputs=['gelu_out'])
    hardsigmoid_node = helper.make_node(
        'HardSigmoid', inputs=['gelu_out'], outputs=['hardsigmoid_out'],
        alpha=0.2, beta=0.5)
    celu_node = helper.make_node(
        'Celu', inputs=['hardsigmoid_out'], outputs=['celu_out'], alpha=1.0)
    erf_node = helper.make_node(
        'Erf', inputs=['celu_out'], outputs=['erf_out'])
    softplus_node = helper.make_node(
        'Softplus', inputs=['erf_out'], outputs=['softplus_out'])
    softsign_node = helper.make_node(
        'Softsign', inputs=['softplus_out'], outputs=['softsign_out'])
    thresholdedrelu_node = helper.make_node(
        'ThresholdedRelu', inputs=['softsign_out'],
        outputs=['thresholdedrelu_out'], alpha=0.5)
    hardmax_node = helper.make_node(
        'Hardmax', inputs=['thresholdedrelu_out'], outputs=['hardmax_out'],
        axis=2)
    logsoftmax_node = helper.make_node(
        'LogSoftmax', inputs=['hardmax_out'], outputs=['logsoftmax_out'],
        axis=2)
    nodes = [
        neg_node, pow_node, gelu_node, hardsigmoid_node, celu_node,
        erf_node, softplus_node, softsign_node, thresholdedrelu_node,
        hardmax_node, logsoftmax_node,
    ]
    return nodes


def _make_elementwise_where_nodes(initializer_list):
    """逐元素运算 + Where: Max/Min/Sum/Mod 后按条件选择"""
    mod_divisor = helper.make_tensor(
        'mod_divisor', TensorProto.FLOAT, [], [1.5])
    initializer_list.append(mod_divisor)
    max_node = helper.make_node(
        'Max', inputs=['logsoftmax_out', 'Y'], outputs=['max_out'])
    min_node = helper.make_node(
        'Min', inputs=['max_out', 'Y'], outputs=['min_out'])
    sum_node = helper.make_node(
        'Sum', inputs=['min_out', 'max_out', 'Y'], outputs=['sum_out'])
    mod_node = helper.make_node(
        'Mod', inputs=['sum_out', 'mod_divisor'], outputs=['mod_out'],
        fmod=1)
    greater_node = helper.make_node(
        'Greater', inputs=['logsoftmax_out', 'Y'],
        outputs=['cascade_cond'])
    where_node = helper.make_node(
        'Where', inputs=['cascade_cond', 'mod_out', 'pow_out'],
        outputs=['where_out'])
    nodes = [max_node, min_node, sum_node, mod_node,
             greater_node, where_node]
    return nodes


def _make_reduction_nodes(initializer_list):
    """归约级联: ReduceL1/ReduceL2/ReduceProd (opset18起axes作为输入)"""
    reduce_cascade_axes = helper.make_tensor(
        'reduce_cascade_axes', TensorProto.INT64, [1], [1])
    initializer_list.append(reduce_cascade_axes)
    reducel1_node = helper.make_node(
        'ReduceL1', inputs=['where_out', 'reduce_cascade_axes'],
        outputs=['reducel1_out'], keepdims=1)
    reducel2_node = helper.make_node(
        'ReduceL2', inputs=['where_out', 'reduce_cascade_axes'],
        outputs=['reducel2_out'], keepdims=1)
    reduceprod_node = helper.make_node(
        'ReduceProd', inputs=['where_out', 'reduce_cascade_axes'],
        outputs=['reduceprod_out'], keepdims=1)
    nodes = [reducel1_node, reducel2_node, reduceprod_node]
    return nodes


def _make_shape_topk_trilu_nodes(initializer_list):
    """形状/检索类: TopK(取值+索引) Trilu(三角矩阵) Shape(动态形状)"""
    cascade_2d_shape = helper.make_tensor(
        'cascade_2d_shape', TensorProto.INT64, [2], [4, 4])
    initializer_list.append(cascade_2d_shape)
    reshape_2d_node = helper.make_node(
        'Reshape', inputs=['where_out', 'cascade_2d_shape'],
        outputs=['where_2d'])
    # TopK的K必须是一维且恰好1个元素, 标量会触发ORT ShapeInferenceError
    topk_k = helper.make_tensor('topk_k', TensorProto.INT64, [1], [2])
    initializer_list.append(topk_k)
    topk_node = helper.make_node(
        'TopK', inputs=['where_2d', 'topk_k'],
        outputs=['topk_values', 'topk_indices'], axis=-1)
    trilu_k = helper.make_tensor('trilu_k', TensorProto.INT64, [], [0])
    initializer_list.append(trilu_k)
    trilu_node = helper.make_node(
        'Trilu', inputs=['where_2d', 'trilu_k'], outputs=['trilu_out'],
        upper=1)
    shape_node = helper.make_node(
        'Shape', inputs=['where_out'], outputs=['where_shape'])
    shape_cast_node = helper.make_node(
        'Cast', inputs=['where_shape'], outputs=['where_shape_f'],
        to=TensorProto.FLOAT)
    nodes = [reshape_2d_node, topk_node, trilu_node,
             shape_node, shape_cast_node]
    return nodes


def _make_onehot_nodes(initializer_list):
    """OneHot: 复用TopK索引(值域0..3)展开为depth=4的one-hot矩阵"""
    topk_flat_shape = helper.make_tensor(
        'topk_flat_shape', TensorProto.INT64, [1], [8])
    initializer_list.append(topk_flat_shape)
    topk_reshape_node = helper.make_node(
        'Reshape', inputs=['topk_indices', 'topk_flat_shape'],
        outputs=['topk_indices_flat'])
    onehot_depth = helper.make_tensor(
        'onehot_depth', TensorProto.INT64, [], [4])
    onehot_values = helper.make_tensor(
        'onehot_values', TensorProto.FLOAT, [2], [0.0, 1.0])
    initializer_list.extend([onehot_depth, onehot_values])
    onehot_node = helper.make_node(
        'OneHot',
        inputs=['topk_indices_flat', 'onehot_depth', 'onehot_values'],
        outputs=['onehot_out'], axis=-1)
    return [topk_reshape_node, onehot_node]


def _make_unique_nodes(initializer_list):
    """Unique: 输出长度动态。micro coder(unique_onnx_base_coder)要求
    UniqueOnnx变长输出只允许终端输出("only support a terminal
    QuantDTypeCast consumer"), 任何中间消费(如Gather)都会在codegen阶段
    报错; v2~v6的常量索引Gather收敛方案能通过infershape但被codegen拒绝,
    故unique_vals直接作为图的第二个输出, 不再汇入Z"""
    cascade_flat_shape = helper.make_tensor(
        'cascade_flat_shape', TensorProto.INT64, [1], [16])
    initializer_list.append(cascade_flat_shape)
    unique_in_reshape = helper.make_node(
        'Reshape', inputs=['where_out', 'cascade_flat_shape'],
        outputs=['where_flat'])
    unique_round_node = helper.make_node(
        'Round', inputs=['where_flat'], outputs=['where_rounded'])
    unique_node = helper.make_node(
        'Unique', inputs=['where_rounded'], outputs=['unique_vals'],
        sorted=1)
    return [unique_in_reshape, unique_round_node, unique_node]


def _make_quant_integer_nodes(initializer_list):
    """整数卷积: ConvInteger(uint8输入int32累加输出)"""
    nchw_shape = helper.make_tensor(
        'nchw_shape', TensorProto.INT64, [4], [1, 1, 4, 4])
    initializer_list.append(nchw_shape)
    nchw_reshape_node = helper.make_node(
        'Reshape', inputs=['where_out', 'nchw_shape'],
        outputs=['where_nchw'])
    cascade_zero = helper.make_tensor(
        'cascade_zero', TensorProto.FLOAT, [], [0.0])
    initializer_list.append(cascade_zero)
    relu_node = helper.make_node(
        'Max', inputs=['where_nchw', 'cascade_zero'],
        outputs=['quant_branch_in'])
    quant_x_cast_node = helper.make_node(
        'Cast', inputs=['quant_branch_in'], outputs=['quant_x_u8'],
        to=TensorProto.UINT8)
    ciconv_w = helper.make_tensor(
        'ciconv_w', TensorProto.UINT8, [1, 1, 3, 3],
        [2, 1, 2, 1, 3, 1, 2, 1, 2])
    ciconv_x_zp = helper.make_tensor(
        'ciconv_x_zp', TensorProto.UINT8, [], [0])
    ciconv_w_zp = helper.make_tensor(
        'ciconv_w_zp', TensorProto.UINT8, [], [0])
    initializer_list.extend([ciconv_w, ciconv_x_zp, ciconv_w_zp])
    convinteger_node = helper.make_node(
        'ConvInteger',
        inputs=['quant_x_u8', 'ciconv_w', 'ciconv_x_zp', 'ciconv_w_zp'],
        outputs=['ciconv_y_i32'])
    ciconv_cast_node = helper.make_node(
        'Cast', inputs=['ciconv_y_i32'], outputs=['ciconv_y_f'],
        to=TensorProto.FLOAT)
    nodes = [
        nchw_reshape_node, relu_node, quant_x_cast_node,
        convinteger_node, ciconv_cast_node,
    ]
    return nodes


def _make_matmul_integer_nodes(initializer_list):
    """原生MatmulInteger(纯两输入A/B形式, 省略可选zero_point):
    模型输入X/Y各自整形[4,4]转int8后做整数矩阵乘, 输出int32

    CI镜像ORT未注册该算子kernel(13/20/21/22实测均报No Op registered),
    gen_dataset加载时会在*_converted.onnx临时副本中将该节点替换为恒等的
    Cast->MatMul->Cast子图(int8点积在float32中精确可表示)以生成参考值;
    原始.onnx保持原生算子, converter/micro测试的即原生MatmulInteger。
    """
    matint_2d_shape = helper.make_tensor(
        'matint_2d_shape', TensorProto.INT64, [2], [4, 4])
    initializer_list.append(matint_2d_shape)
    matint_a_reshape_node = helper.make_node(
        'Reshape', inputs=['X', 'matint_2d_shape'],
        outputs=['matint_a_2d'])
    matint_b_reshape_node = helper.make_node(
        'Reshape', inputs=['Y', 'matint_2d_shape'],
        outputs=['matint_b_2d'])
    # CI随机输入[-5,5], 转int8不饱和, |点积和|<=16*5*5=400, 精确可表示
    matint_a_cast_node = helper.make_node(
        'Cast', inputs=['matint_a_2d'], outputs=['matint_a_i8'],
        to=TensorProto.INT8)
    matint_b_cast_node = helper.make_node(
        'Cast', inputs=['matint_b_2d'], outputs=['matint_b_i8'],
        to=TensorProto.INT8)
    matmulinteger_node = helper.make_node(
        'MatMulInteger', inputs=['matint_a_i8', 'matint_b_i8'],
        outputs=['matint_y_i32'])
    matint_cast_node = helper.make_node(
        'Cast', inputs=['matint_y_i32'], outputs=['matint_y_f'],
        to=TensorProto.FLOAT)
    return [matint_a_reshape_node, matint_b_reshape_node,
            matint_a_cast_node, matint_b_cast_node,
            matmulinteger_node, matint_cast_node]


def _append_row_reshape(nodes, initializer_list, src_name, row_name, width):
    """将任意静态形状张量整形为[1, width]行向量便于拼接"""
    row_shape = helper.make_tensor(
        f'{row_name}_shape', TensorProto.INT64, [2], [1, width])
    initializer_list.append(row_shape)
    nodes.append(helper.make_node(
        'Reshape', inputs=[src_name, f'{row_name}_shape'],
        outputs=[row_name]))
    return row_name


def create_cascademodel_onnx_model(output_path):
    logging.info(f"creating cascade ops model: {output_path}")
    input_shape = [1, 4, 4]
    input_x = helper.make_tensor_value_info(
        'X', TensorProto.FLOAT, input_shape)
    input_y = helper.make_tensor_value_info(
        'Y', TensorProto.FLOAT, input_shape)
    initializer_list = []
    nodes_chain = _make_activation_chain_nodes(initializer_list)
    nodes_elementwise = _make_elementwise_where_nodes(initializer_list)
    nodes_reduce = _make_reduction_nodes(initializer_list)
    nodes_search = _make_shape_topk_trilu_nodes(initializer_list)
    nodes_onehot = _make_onehot_nodes(initializer_list)
    nodes_unique = _make_unique_nodes(initializer_list)
    nodes_quant = _make_quant_integer_nodes(initializer_list)
    nodes_matint = _make_matmul_integer_nodes(initializer_list)
    # TopK索引转float后拼接。v5实测Cast直接以TopK输出为输入时该路径的
    # 形状推断在converter量化段丢失(topk_indices->Cast->Reshape所在的
    # Concat-op3失败), 而同为TopK输出的values行及其余对照行均通过;
    # v6改为经已验证正常的Reshape张量topk_indices_flat(喂OneHot的分支,
    # v4/v5两轮均通过)后再Cast
    topk_indices_cast_node = helper.make_node(
        'Cast', inputs=['topk_indices_flat'], outputs=['topk_indices_f'],
        to=TensorProto.FLOAT)
    row_nodes = [topk_indices_cast_node]
    _append_row_reshape(row_nodes, initializer_list,
                        'where_out', 'where_row', 16)
    _append_row_reshape(row_nodes, initializer_list,
                        'mod_out', 'mod_row', 16)
    _append_row_reshape(row_nodes, initializer_list,
                        'reducel1_out', 'reducel1_row', 4)
    _append_row_reshape(row_nodes, initializer_list,
                        'reducel2_out', 'reducel2_row', 4)
    _append_row_reshape(row_nodes, initializer_list,
                        'reduceprod_out', 'reduceprod_row', 4)
    _append_row_reshape(row_nodes, initializer_list,
                        'topk_values', 'topk_values_row', 8)
    _append_row_reshape(row_nodes, initializer_list,
                        'topk_indices_f', 'topk_indices_row', 8)
    _append_row_reshape(row_nodes, initializer_list,
                        'trilu_out', 'trilu_row', 16)
    _append_row_reshape(row_nodes, initializer_list,
                        'where_shape_f', 'shape_row', 3)
    _append_row_reshape(row_nodes, initializer_list,
                        'onehot_out', 'onehot_row', 32)
    _append_row_reshape(row_nodes, initializer_list,
                        'ciconv_y_f', 'ciconv_row', 4)
    _append_row_reshape(row_nodes, initializer_list,
                        'matint_y_f', 'matint_row', 16)
    # v6定位完成后恢复单段拼接: TopK行的Cast已改经topk_indices_flat转接
    # (v6实测全部Concat推断通过, 顺利进入codegen阶段); unique行因micro
    # coder变长输出限制改为独立图输出, 不再汇入Z
    # 列宽 = 16+16+4+4+4+8+8+16+3+32+4+16 = 131
    concat_final_node = helper.make_node(
        'Concat',
        inputs=['where_row', 'mod_row', 'reducel1_row', 'reducel2_row',
                'reduceprod_row', 'topk_values_row', 'topk_indices_row',
                'trilu_row', 'shape_row', 'onehot_row', 'ciconv_row',
                'matint_row'],
        outputs=['Z'], axis=1)
    all_nodes = (
        nodes_chain + nodes_elementwise + nodes_reduce + nodes_search +
        nodes_onehot + nodes_unique + nodes_quant + nodes_matint +
        row_nodes + [concat_final_node]
    )
    graph = helper.make_graph(
        all_nodes,
        # 图名带版本号: CI上可用 onnx.load(...)后打印graph.name 验证转换的
        # 是否为最新生成(旧模型名无_v7后缀), 排除"改了py但转的还是旧onnx"
        'cascade_ops_graph_v7',
        [input_x, input_y],
        # Z必须为第0个输出: ai_daily的build_save取output_0.npy,
        # 精度比对按输出顺序与output_{k}.npy一一对应;
        # unique_vals(变长)按micro coder要求作终端输出, 以符号维声明动态长度
        [helper.make_tensor_value_info('Z', TensorProto.FLOAT, [1, 131]),
         helper.make_tensor_value_info('unique_vals', TensorProto.FLOAT,
                                       ['num_unique'])],
        initializer=initializer_list
    )
    # 模型直接含原生MatmulInteger; gen_dataset的ORT加载失败时会在
    # *_converted.onnx临时副本中做恒等替换生成参考值, 本文件保持原样。
    # (v5曾尝试随文件下发中间value_info静态shape, 实测converter不读取,
    # 已连同__init__.py的infer_value_info参数一并回退)
    create_low_ir_version_model(
        graph, producer_name='cascade-ops-generator',
        output_path=output_path, opset_version=20)
    logging.info(f"cascade ops model saved: {output_path}")
