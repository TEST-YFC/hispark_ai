# coding: utf-8
"""hs-verify-op-host operator spec — THE ONLY FILE YOU WRITE PER OPERATOR.

Copy to your operator project's  scripts/op_spec.py  and fill it in. The fixed harness
(run_all_cases.py) imports this module and drives the whole internal step1->step5 pipeline.
You design the test cases and build the models; the harness computes the reference
outputs, runs the benchmark, and parses the real cosine — you NEVER write a cosine
number or an "expected" tensor here.

Required names (validated by the harness):
    OP_NAME            : str
    ONNX_TEST_CASES    : list[dict]   each {"id", "desc", "params": {...}}
    TFLITE_TEST_CASES  : list[dict]   designed independently per TFLite spec (NHWC)
    build_onnx_model(tc, model_path)     -> writes a .onnx file (NCHW)
    build_tflite_model(tc, model_path)   -> writes a .tflite file (NHWC)
    make_inputs(tc, framework)           -> list[np.ndarray] in model-input order
Required when the corresponding framework case list is non-empty:
    ONNX_TARGET_OP_TYPE     : str        exact ONNX node op_type. The harness loads EVERY
                                        generated .onnx and fails if the target node is absent.
    PARAM_COLUMNS          : list[str]  tc["params"] keys to show as Excel columns
    TFLITE_TARGET_BUILTIN  : int        builtin number from existence verification
                                        (kTfLiteBuiltin<Op> = N). The harness unpacks EVERY
                                        built .tflite and fails the case if the target
                                        builtin is absent — the TF converter normalizes ops
                                        by shape (e.g. same-shape calls to a broadcast op
                                        lower to its non-broadcast sibling), and without
                                        this assertion such cases silently test another op.
    INT8_KERNEL_SYMBOL     : str | list[str] | ""   the C function the operator's int8
                                        kernel exposes (default: f"{OP_NAME}Int8", the nnacl
                                        convention — HardmaxInt8, SoftmaxInt8, ...). After
                                        each riscv_int8 run the harness greps the generated
                                        net*.c for a CALL to this symbol; absent -> the case
                                        FAILs as INT8_NOT_GENUINE, because quantization
                                        bypassing the op emits the FP32 opcoder and every
                                        int8 cosine prints a flat 1.000000 (green but never
                                        quantized — the trap). Override only if the op's int8
                                        codegen genuinely uses a different name. Set to ""
                                        (empty) ONLY for an int8-EXEMPT op (output non-float /
                                        pure index) to disable the check — never to dodge a
                                        real fallback. This is the discriminator that flat-1.0
                                        heuristics get wrong: discrete-output ops (hardmax/
                                        argmax/select) legitimately print cos=1.0 even with
                                        genuine int8, so symbol presence — not the cosine — is
                                        what proves the int8 path ran.

Design rules (see SKILL.md 五):
  * Two case sets are INDEPENDENT — ONNX uses ONNX spec/NCHW, TFLite uses TFLite spec/NHWC.
  * 10-20 cases per framework covering attribute bounds / shapes / value edges / dtypes.
  * Inputs MUST be deterministic (no random) so results are reproducible.
  * MSLite converts int64 -> int32 internally; store index-like inputs as np.int32.

Multi-input / broadcasting operators (the example below is single-input — adapt):
  * make_inputs returns ALL model inputs in order (e.g. [a, b] or [cond, x, y]), not just one.
  * Non-float inputs keep their own dtype — bool masks as np.bool_, indices as np.int32.
    The quantizer only quantizes float inputs; don't give a bool/int input a value-domain fill.
  * build_*_model declares each input with its own shape; broadcasting ops give inputs
    DIFFERENT shapes and set the output to their broadcast shape (np.broadcast_shapes).
  * Cover only the broadcast forms the op's SPEC actually supports — same-shape always; add
    scalar (one input = [1]) and any documented form (full NumPy broadcast, leading-dim only…).
    Don't design forms the op rejects. See the commented multi-input pattern at file end.

The example below verifies HardSwish (no attributes) for both frameworks; replace it.
"""

import numpy as np

OP_NAME = "HardSwish"
ONNX_TARGET_OP_TYPE = "HardSwish"
PARAM_COLUMNS = ["shape", "value_domain"]
# 存在性查证命中的 builtin 编号（kTfLiteBuiltinHardSwish = 117）。harness 据此解包校验每个
# 生成的 .tflite 确含目标 builtin——换算子时一并改成你查证命中的编号，不要删。
TFLITE_TARGET_BUILTIN = 117
# HardSwish 是激活子类型：int8 走共享的 activation int8 coder，生成代码里调的是 HSwishInt8，
# 不是默认推断的 "HardSwishInt8"。这正是需要显式声明 INT8_KERNEL_SYMBOL 的典型场景——
# 默认值（f"{OP_NAME}Int8"）对独立 PrimType 算子（如 Hardmax→HardmaxInt8）才成立。
INT8_KERNEL_SYMBOL = "HSwishInt8"

# ---- ONNX cases (NCHW) -------------------------------------------------------
ONNX_TEST_CASES = [
    # --- shape 覆盖 ---
    {"id": 1,  "desc": "2D 基本",            "params": {"shape": [1, 8],        "value_domain": "mixed"}},
    {"id": 2,  "desc": "4D 小张量",           "params": {"shape": [1, 3, 4, 4],   "value_domain": "mixed"}},
    {"id": 3,  "desc": "4D 大张量",           "params": {"shape": [1, 32, 64, 64],"value_domain": "mixed"}},
    {"id": 4,  "desc": "batch>1",            "params": {"shape": [4, 8],         "value_domain": "mixed"}},
    # --- 值域（sign domain）覆盖 — INT8 zp 偏向关键 ---
    {"id": 5,  "desc": "全正数",             "params": {"shape": [1, 16],        "value_domain": "positive"}},
    {"id": 6,  "desc": "全负数",             "params": {"shape": [1, 16],        "value_domain": "negative"}},
    {"id": 7,  "desc": "小量级(接近零)",     "params": {"shape": [1, 16],        "value_domain": "near_zero"}},
    {"id": 8,  "desc": "全零(退化)",         "params": {"shape": [1, 16],        "value_domain": "zeros"}},
    # --- 算子敏感区间（HardSwish 示例：x<-3 饱和为0、-3≤x≤3 非线性段、x>3 线性段） ---
    {"id": 9,  "desc": "饱和区(x<-3)",       "params": {"shape": [1, 16],        "value_domain": "hs_saturate_neg"}},
    {"id": 10, "desc": "非线性段(-3≤x≤3)",   "params": {"shape": [1, 16],        "value_domain": "hs_nonlinear"}},
    {"id": 11, "desc": "线性段(x>3)",        "params": {"shape": [1, 16],        "value_domain": "hs_linear"}},
]

# ---- TFLite cases (NHWC) — designed independently ---------------------------
TFLITE_TEST_CASES = [
    # --- shape 覆盖 ---
    {"id": 1,  "desc": "2D 基本",            "params": {"shape": [1, 8],        "value_domain": "mixed"}},
    {"id": 2,  "desc": "4D 小张量",           "params": {"shape": [1, 4, 4, 3],  "value_domain": "mixed"}},
    {"id": 3,  "desc": "4D 大张量",           "params": {"shape": [1, 64, 64, 3],"value_domain": "mixed"}},
    {"id": 4,  "desc": "batch>1",            "params": {"shape": [4, 8],         "value_domain": "mixed"}},
    # --- 值域覆盖 ---
    {"id": 5,  "desc": "全正数",             "params": {"shape": [1, 16],        "value_domain": "positive"}},
    {"id": 6,  "desc": "全负数",             "params": {"shape": [1, 16],        "value_domain": "negative"}},
    {"id": 7,  "desc": "小量级(接近零)",     "params": {"shape": [1, 16],        "value_domain": "near_zero"}},
    {"id": 8,  "desc": "全零(退化)",         "params": {"shape": [1, 16],        "value_domain": "zeros"}},
    # --- 算子敏感区间 ---
    {"id": 9,  "desc": "饱和区(x<-3)",       "params": {"shape": [1, 16],        "value_domain": "hs_saturate_neg"}},
    {"id": 10, "desc": "非线性段(-3≤x≤3)",   "params": {"shape": [1, 16],        "value_domain": "hs_nonlinear"}},
    {"id": 11, "desc": "线性段(x>3)",        "params": {"shape": [1, 16],        "value_domain": "hs_linear"}},
]


def build_onnx_model(tc, model_path):
    """Build a single-op ONNX model (NCHW) for this case and save it."""
    import onnx
    from onnx import helper, TensorProto

    shape = tc["params"]["shape"]
    x = helper.make_tensor_value_info("input", TensorProto.FLOAT, shape)
    y = helper.make_tensor_value_info("output", TensorProto.FLOAT, shape)
    node = helper.make_node("HardSwish", ["input"], ["output"])
    graph = helper.make_graph([node], f"{OP_NAME}_g", [x], [y])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 14)])
    model.ir_version = 8
    onnx.checker.check_model(model)
    onnx.save(model, model_path)


def build_tflite_model(tc, model_path):
    """Build a single-op TFLite model (NHWC). Express the op out of tf primitives so
    the converter folds it into the intended builtin (here: HARD_SWISH)."""
    import tensorflow as tf

    shape = tc["params"]["shape"]

    class OpModel(tf.Module):
        @tf.function(input_signature=[tf.TensorSpec(shape=shape, dtype=tf.float32, name="input")])
        def __call__(self, x):
            return x * tf.nn.relu6(x + 3.0) / 6.0  # -> HARD_SWISH

    m = OpModel()
    conv = tf.lite.TFLiteConverter.from_concrete_functions(
        [m.__call__.get_concrete_function()], m)
    conv.experimental_new_converter = False  # align with the WS63 toolchain
    with open(model_path, "wb") as f:
        f.write(conv.convert())


def make_distinct_axis_inputs(shape, axis, lo=-127.0, hi=127.0):
    """沿目标轴等距铺开取值（间距远大于 INT8 量化桶宽），其余维广播复制。

    序关系类算子（argmax/hardmax/topk/sort/select-by-max 等输出由输入"谁更大"决定的算子）
    的 int8 用例必须用这种数据：普通 linspace 在大张量下相邻值间距 < 量化桶宽
    （全幅/254），多个浮点不同的值落进同一 int8 桶，int8 的 argmax 位置就会偏离
    fp32 参考——这不是 kernel bug，是测试数据设计缺陷（详见 hs-dev-op-implement
    references/int8-coder-conventions.md §2b；实证：Hardmax 大 4D 用例两次 FAIL 烧掉
    一轮完整验证，根因正是 linspace 量化碰撞）。"""
    axis = axis % len(shape)
    ramp = np.linspace(lo, hi, shape[axis], dtype=np.float32)
    view = [1] * len(shape)
    view[axis] = shape[axis]
    return np.broadcast_to(ramp.reshape(view), shape).copy()


def make_inputs(tc, framework):
    """Return ordered list[np.ndarray] for this case. Deterministic only.

    IMPORTANT — INT8 calibration data integrity:
      The harness uses the SAME make_inputs() data for both calibration and inference
      (calib_dir is a byte-copy of input_files). So every value domain you cover here
      directly determines which sign domains / operator regions get quantized correctly.

      Design checklist per operator:
      1. One baseline: linspace across mixed sign range (e.g. [-6.0, 6.0])
      2. One all-positive + one all-negative — exercises INT8 zp bias
      3. One all-zero — degenerate-input robustness
      4. One per operator-specific sensitive region (see tc["params"]["value_domain"])
      5. 序关系类算子（argmax/hardmax/topk/sort 等）：凡进 int8 通路的用例，
         沿目标轴的数据一律用上方 make_distinct_axis_inputs() 生成——
         保证相邻值间距 > 量化桶宽，否则大张量必现量化碰撞 FAIL（见该函数 docstring）

    VALUE DOMAIN MAP (keyed by tc["params"]["value_domain"]):
      mixed             [-6.0, 6.0]   baseline: positive + negative
      positive          [0.1, 6.0]    all-positive, zp pushes to one side
      negative          [-6.0, -0.1]  all-negative, zp pushes to other side
      near_zero         [-1e-6, 1e-6] tiny scale, stresses quantization resolution
      zeros             all 0.0       degenerate input

    Operator-specific (HardSwish example — replace with YOUR operator's regions):
      hs_saturate_neg   [-6.0, -3.1]  x<-3: HardSwish output = 0 (saturation)
      hs_nonlinear      [-3.0, 3.0]   -3≤x≤3: nonlinear transition
      hs_linear         [3.1, 6.0]    x>3: linear passthrough
    """
    shape = tc["params"]["shape"]
    n = int(np.prod(shape))
    d = tc["params"].get("value_domain", "mixed")

    if d == "zeros":
        arr = np.zeros(shape, dtype=np.float32)
    elif d == "positive":
        arr = np.linspace(0.1, 6.0, n, dtype=np.float32).reshape(shape)
    elif d == "negative":
        arr = np.linspace(-6.0, -0.1, n, dtype=np.float32).reshape(shape)
    elif d == "near_zero":
        arr = np.linspace(-1e-6, 1e-6, n, dtype=np.float32).reshape(shape)
    # --- operator-specific: HardSwish regions ---
    elif d == "hs_saturate_neg":
        arr = np.linspace(-6.0, -3.1, n, dtype=np.float32).reshape(shape)
    elif d == "hs_nonlinear":
        arr = np.linspace(-3.0, 3.0, n, dtype=np.float32).reshape(shape)
    elif d == "hs_linear":
        arr = np.linspace(3.1, 6.0, n, dtype=np.float32).reshape(shape)
    else:  # "mixed" (baseline)
        arr = np.linspace(-6.0, 6.0, n, dtype=np.float32).reshape(shape)
    return [arr]


# ---------------------------------------------------------------------------
# Reference pattern for MULTI-INPUT / BROADCASTING ops (commented — adapt, don't keep as-is).
# Per-input shapes come from params; output shape is their NumPy broadcast. make_inputs
# returns every model input in order, each with its own shape and dtype.
#
# def _shapes(tc):
#     s = tc["params"]["shape"]; p = tc["params"]
#     a, b = p.get("a_shape", s), p.get("b_shape", s)          # default to shared "shape"
#     return a, b, list(np.broadcast_shapes(tuple(a), tuple(b)))
#
# def make_inputs(tc, framework):                              # e.g. a 2-float-input op
#     a_shape, b_shape, _ = _shapes(tc)
#     a = np.linspace(-6.0, 6.0, int(np.prod(a_shape)), np.float32).reshape(a_shape)
#     b = np.linspace(6.0, -6.0, int(np.prod(b_shape)), np.float32).reshape(b_shape)
#     return [a, b]
#
# Broadcast cases then differ only in shape. For full-NumPy-broadcast ops, cover ALL of:
#   {"id": 12, "desc": "scalar-b broadcast",  "params": {"shape": [2, 4],    "b_shape": [1]}}
#   {"id": 13, "desc": "middle-dim broadcast","params": {"shape": [2, 3, 4], "b_shape": [2, 1, 4]}}
#   {"id": 14, "desc": "mixed: scalar + non-trivial", "params": {"shape": [2, 3, 4],
#                                                     "a_shape": [1], "b_shape": [2, 1, 4]}}
# Why these two extra forms: kernels often add fast paths guarded by weak conditions —
#   * an `i % num` index approximation is only accidentally right for OUTERMOST-dim
#     broadcast; the middle-dim case ([2,1,4] vs [2,3,4]) reads wrong elements;
#   * an "any input is scalar -> fast path" guard lets the OTHER, still-broadcasting input
#     through unbroadcast; only the mixed case (scalar + non-trivial together) exposes it.
# Same-shape-only or scalar-only coverage proves nothing about either failure mode.
# A non-float input (bool mask / int indices) keeps its dtype, e.g. np.zeros(cs, np.bool_).
# ---------------------------------------------------------------------------
