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
# 级联算子覆盖用例: Gelu Pack Unpack Fill SelectV2 Select Shape TopK Neg
# Pow ReverseV2 Maximum Minimum OneHot Unique ReduceProd LogSoftmax GatherNd
# 双输出模型: merged为主输出(第0个), unique的u_val(变长)为第1个输出;
# Unique变长输出按micro coder要求必须终端输出, 不能作为中间张量消费
import logging
import tensorflow as tf
import numpy as np

logging.basicConfig(level=logging.NOTSET)


class _cascadeoperatormodel(tf.Module):
    def __init__(self):
        super(_cascadeoperatormodel, self).__init__()
        self.pow_exp = tf.Variable(
            tf.constant(2.0, dtype=tf.float32),
            trainable=False, name="pow_exp"
        )

    @tf.function(input_signature=[
        tf.TensorSpec(shape=[1, 2, 2], dtype=tf.float32, name="input")
    ])
    def __call__(self, x):
        main = self._run_math_chain(x)
        rows, u_val = self._run_search_and_struct_nodes(main)
        merged = tf.concat(rows, axis=1, name="merged_output")
        # Unique变长输出按micro coder要求作为终端输出, 与merged同为模型输出
        # (merged为第0个, ai_daily的build_save与精度比对均按输出顺序对应)
        return merged, u_val

    def _run_math_chain(self, x):
        """数学/激活级联: Neg Pow Gelu LogSoftmax Maximum Minimum ReduceProd"""
        n = tf.negative(x, name="neg")
        p = tf.pow(x, self.pow_exp, name="pow")
        g = tf.nn.gelu(p, name="gelu")
        ls = tf.nn.log_softmax(g, axis=-1, name="log_softmax")
        mx = tf.maximum(ls, n, name="maximum")
        mn = tf.minimum(mx, 0.5, name="minimum")
        rp = tf.math.reduce_prod(mn, axis=1, keepdims=True,
                                 name="reduce_prod")
        return {"n": n, "g": g, "ls": ls, "mx": mx, "mn": mn, "rp": rp}

    def _run_search_and_struct_nodes(self, m):
        """检索/结构级联: TopK ReverseV2 Shape Fill Pack Unpack Select
        SelectV2 OneHot Unique GatherNd, 各分支整形为[1, k]行向量"""
        mn = m["mn"]
        g = m["g"]
        mn2d = tf.reshape(mn, [2, 2], name="mn_2d")
        tv, ti = tf.math.top_k(mn2d, k=2, name="top_k")
        rv = tf.reverse(mn, axis=[1], name="reverse_v2")
        # Pack按行堆叠 / Unpack按行拆解
        r0 = tf.reshape(rv[:, 0, :], [2], name="pack_in0")
        r1 = tf.reshape(rv[:, 1, :], [2], name="pack_in1")
        pk = tf.stack([r0, r1], axis=0, name="pack")
        u0, u1 = tf.unstack(pk, num=2, axis=0, name="unpack")
        # Select: 同形三输入(TF2中tf.where三参恒为SelectV2, Select v1需raw_ops)
        # SelectV2: 条件广播
        # raw_ops.Select仅接受关键字传参且形参名随TF版本变化: CI镜像为
        # condition/x/y(老版本为condition/t/e), 绑定层名不影响图节点op类型
        sel_cond = tf.greater(u0, u1, name="select_cond")
        sel = tf.raw_ops.Select(condition=sel_cond, x=u0, y=u1, name="select")
        v2_cond = tf.greater(u0, 0.0, name="selectv2_cond")
        selv2 = tf.where(v2_cond, rv, tf.negative(rv, name="neg_y"),
                         name="select_v2")
        # OneHot: TopK索引值域0..1, depth=2
        ti_flat = tf.reshape(ti, [4], name="topk_indices_flat")
        oh = tf.one_hot(ti_flat, 2, name="one_hot")
        # Unique: 输出长度动态(tflite中shape signature为[-1]); micro coder
        # 与ONNX侧UniqueOnnx同限(变长输出仅允许终端输出), slice/reduce等
        # 中间消费会被codegen拒绝, 故u_val直接作为模型第二个输出,
        # 不再汇入merged
        g_flat = tf.reshape(g, [4], name="gelu_flat")
        u_in = tf.cast(tf.round(g_flat), tf.int32, name="unique_in")
        u_val, _ = tf.unique(u_in, name="unique")
        # Shape/Fill: fill的dims改用静态张量g_flat的形状(覆盖Shape/Fill
        # 算子即可); 若dims取unique的动态长度, fill输出signature为[-1],
        # 变长中间张量同样会触碰micro coder的终端输出限制
        sh = tf.shape(g_flat, name="shape")
        fl = tf.fill(sh, 0.25, name="fill")
        fl_first = tf.slice(fl, [0], [1], name="fill_first")
        # keepdims=True保持rank-1的[1]输出, 避免标量(rank-0)在reshape/
        # concat推断中与"形状未知"混淆
        fsum = tf.reduce_sum(fl_first, keepdims=True, name="fill_sum")
        # GatherNd: 常量索引取对角元素
        rv2d = tf.reshape(rv, [2, 2], name="rv_2d")
        gn = tf.gather_nd(rv2d, [[0, 0], [1, 1]], name="gather_nd")
        sh_f = tf.cast(sh, tf.float32, name="shape_f")
        rows = [
            tf.reshape(g, [1, 4], name="gelu_row"),
            tf.reshape(m["ls"], [1, 4], name="logsoftmax_row"),
            tf.reshape(m["mx"], [1, 4], name="maximum_row"),
            tf.reshape(mn, [1, 4], name="minimum_row"),
            tf.reshape(m["rp"], [1, 2], name="reduceprod_row"),
            # ONNX侧v5实测: Cast直接消费TopK输出会使converter量化段对该
            # 路径的形状推断丢失(所在Concat报InferShape failed), 先Reshape
            # 成静态形状再Cast(与OneHot消费TopK索引的已验证路径一致)
            tf.reshape(tf.cast(tf.reshape(tv, [4], name="topk_values_flat"),
                       tf.float32, name="topk_values_f"), [1, 4],
                       name="topk_values_row"),
            tf.reshape(tf.cast(ti_flat, tf.float32, name="topk_indices_f"),
                       [1, 4], name="topk_indices_row"),
            tf.reshape(rv, [1, 4], name="reverse_row"),
            tf.reshape(fsum, [1, 1], name="fill_row"),
            tf.reshape(pk, [1, 4], name="pack_row"),
            tf.reshape(sel, [1, 2], name="select_row"),
            tf.reshape(selv2, [1, 4], name="selectv2_row"),
            tf.reshape(oh, [1, 8], name="onehot_row"),
            tf.reshape(gn, [1, 2], name="gathernd_row"),
            tf.reshape(sh_f, [1, 1], name="shape_row"),
        ]
        return rows, u_val


def create_cascademodel_tflite_model(output_path):
    model = _cascadeoperatormodel()
    concrete_func = model.__call__.get_concrete_function()
    converter = tf.lite.TFLiteConverter.from_concrete_functions(
        [concrete_func])
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.SELECT_TF_OPS
    ]
    converter.allow_custom_ops = True
    tflite_model = converter.convert()
    with open(output_path, "wb") as f:
        f.write(tflite_model)
    logging.info(f"cascade operators tflite model saved: {output_path}")
