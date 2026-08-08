# INT8 OpCoder Conventions

Read this when implementing the INT8 OpCoder for a new operator. These conventions
came from reviewing existing INT8 coders (`hswish_int8_coder.cc`, `relux_int8_coder.cc`,
`leaky_relu_int8_coder.cc`) and are not enforced by the compiler — but skipping them
makes generated MCU code harder to read and debug.

First classify what "int8" means for this operator:

- **Quantized int8 path**: the source operator is float, and `full_quant_quantizer`
  converts tensors to int8 for MCU deployment. The qparam, runtime-kernel mirroring,
  and `support_int8_ops_` rules in this document apply.
- **Native integer path**: the source specification itself uses `int8/uint8/int32/bool`
  inputs or outputs (for example integer convolution, cast, shape/index/control ops).
  Do not invent scale/zp fields or quantizer-list entries just because the dtype is
  int8. Still place integer compute in `nnacl_c/int8/` or `nnacl_c/base/` as appropriate,
  register every spec dtype (`kNumberTypeInt8`, `kNumberTypeUInt8`, ...), and avoid
  `nnacl_c/fp32/` / `opcoders/nnacl/fp32/` unless there is a real float path.

## 1. Mark leaf coder classes `final`

Coder classes not intended for subclassing should use `final` to make intent explicit
and let the compiler devirtualize calls.

```cpp
class HSwishInt8Coder final : public OperatorCoder { /* ... */ };
```

## 2. Mirror the runtime int8 kernel's *exact* multiplier arithmetic

This is the single most important int8 rule, and it overrides any generic
"prefer double" advice. The opcoder-emitted MCU code must reproduce the runtime
int8 kernel (`src/litert/kernel/cpu/int8/<op>_int8.cc`) **bit-for-bit**, because the
converter runs that runtime kernel during `bias_correction` and the MCU output is
compared against it. Use the **same** intermediate type, the same constants, and the
same formula as the kernel.

In this codebase the multiplier is computed in **`float`** (not double), then passed
to `QuantizeMultiplier` (whose parameter is `double`, so the `float` is promoted at
the call). Copy that exactly — do **not** "upgrade" it to `double`, or your generated
code will diverge from the kernel and fail the similarity check.

```cpp
// matches hswish_int8.cc / hswish_int8_coder.cc — float intermediate, float casts:
const float output_multiplier =
  (1.0f / 128.0f) * static_cast<float>(quant_arg_.input_scale) / static_cast<float>(quant_arg_.output_scale);
QuantizeMultiplier(output_multiplier, &mult_fixed, &mult_shift);  // float → double at the call
```

(`QuantizeMultiplier(double, ...)` is declared in `nnacl_c/int8/quantize.h`. The point
is not "double vs float" in the abstract — it's "identical to the runtime kernel".)

### 2a. The "bit-for-bit" rule covers quant-PARAM population too, not just multipliers

The runtime int8 kernel (`src/litert/kernel/cpu/int8/<op>_int8.cc`) and the opcoder
(`opcoders/nnacl/int8/<op>_int8_coder.cc`) **both populate the same `XxxQuantArg`
struct that feeds the same shared `nnacl_c/int8/<op>_int8.c` compute**. So every field
must be filled identically in both — most easily botched is the **zero-point sign
convention**:

- Some ops (e.g. Softmax) store `zp_ = -zeroPoint` because their compute formula adds it
  with a specific sign. If you store `-zeroPoint` in the runtime kernel but `+zeroPoint`
  in the opcoder (or vice-versa), `bias_correction` and the MCU disagree and the
  similarity check fails — even though both "look" reasonable in isolation. **Pick one
  convention, use it in both, and make sure the shared `.c` compute matches it.**
- Decide the convention from the compute: if the `.c` uses the field as the standard
  quantize `q = round(real/scale) + zp`, store the **actual** `zeroPoint` (no negation)
  in both places — this is the canonical form, see `relux_int8.cc` (`zp_ = +zeroPoint`,
  used directly in `relux_int8.c`).
- **Forbidden: the "store `-zeroPoint`, then negate again in the `.c`" round-trip.** It
  nets out to the right value but is non-idiomatic, contradicts the reference kernels, and
  the accompanying comment usually misstates the convention. It typically appears when the
  Softmax template (which legitimately stores `-zeroPoint`) is copied into a `q = ... + zp`
  op without simplifying. If your compute uses `+ zp`, store `+zeroPoint` and use it
  directly in **both** runtime kernel and opcoder; do not inject a compensating negation.
  (Real regression: a generated Hardmax stored `-zeroPoint` in `Prepare` and re-negated in
  the `.c` — correct output, but a fragile cargo-culted fix arrived at through a FAIL round
  rather than understanding the convention.)

### 2b. Only put fields the compute actually uses into `XxxQuantArg`

Don't blindly copy `SoftmaxQuantArg`'s field list. Include only what the `.c` reads.
Example: **Hardmax's argmax is invariant to the input's affine quantization** (a
monotonic positive-scale transform doesn't change which element is the max), so the
input scale/zp are irrelevant — `HardmaxQuantArg` carries only the *output* quant params
(+ activation min/max for clamping). Fewer fields = smaller generated struct = less
codesize, and fewer chances for the runtime/opcoder mismatch in 2a.

Caveat (a quantization limit, not a kernel bug): the invariance only holds while the
elements have *distinct* int8 values. When several distinct floats round into the same
int8 bucket (e.g. linspace [-1,1] over 384 elements → neighbour gap 0.005 < the ~0.008
quant step), the int8 argmax can pick a different position than the float argmax, and
carrying the input scale/zp does **not** help (dequantizing equal int8 values yields
equal floats). So leaving input scale/zp out of the struct is still correct; the right
mitigation is on the test side — keep neighbouring values farther apart than the quant
step so no two elements collide into one bucket. hs-verify-op-host's spec template ships a
ready-made `make_distinct_axis_inputs()` for exactly this — use it for every int8 case
of an ordering-class op when authoring the spec, instead of rediscovering the rule
through a FAIL round.

## 3. Mirror `MS_ASSERT` from the runtime kernel

If the runtime kernel in `src/litert/kernel/cpu/int8/` has an assertion in a helper
(e.g. `MS_ASSERT(input >= 0)` in `MultiplierInt32ToInt16`), replicate it in the
coder's copy of that helper. Add a comment so future readers know where the
authoritative version lives:

```cpp
// Mirrors HSwishInt8CPUKernel::MultiplierInt32ToInt16 in src/litert/kernel/cpu/int8/.
static int16_t MultiplierInt32ToInt16(int32_t input) {
  MS_ASSERT(input >= 0);
  // ...
}
```

## 4. Assign quant params to named locals before checking `.empty()`

Call `input_tensor_->quant_params()` once and store the result. Avoids repeated
calls and reads more cleanly.

```cpp
auto in_quant_args = input_tensor_->quant_params();
MS_CHECK_TRUE_MSG(!in_quant_args.empty(), RET_ERROR,
                  "HSwish int8 input quant param cannot be empty.");
quant_arg_.input_scale = in_quant_args.front().scale;
```

## 5. Op-specific error messages

Prefix `MS_CHECK_TRUE_MSG` strings with the op name so failures are locatable in
converter logs (which mix output from many ops):

```cpp
// Good:
MS_CHECK_TRUE_MSG(..., "HSwish int8 input quant param cannot be empty.");
// Bad — hard to grep, unclear which op:
MS_CHECK_TRUE_MSG(..., "Input quant param cannot be empty.");
```

## 6. Comment non-obvious math formulas

For multiplier computations, add a one-line comment explaining the physical
meaning. The next person to debug a numerical mismatch will thank you.

```cpp
// output_multiplier encodes: (1/128) * input_scale / output_scale  （类型与 runtime kernel 一致，见约定 2）
const float output_multiplier =
  (1.0f / 128.0f) * static_cast<float>(quant_arg_.input_scale) / static_cast<float>(quant_arg_.output_scale);
```

## 7. Use descriptive variable names in generated code

The string passed to `code.CodeStruct("name", ...)` appears verbatim in the
MCU-generated C source. Prefer op-specific names — generated code is much easier
to read this way:

```cpp
// Good — clear in generated code:
code.CodeStruct("hswish_quant_arg", quant_arg_);
// Bad — collides with other ops' generated structs:
code.CodeStruct("quant_arg", quant_arg_);
```

## 8. Header hygiene

Headers must only include what they directly use. Don't copy includes from
reference files without verifying each one is needed in the header (vs. the
`.cc`).

- `nnacl_c/op_base.h` is a pure C header (stdint/stdlib). Don't include it in a
  C++ coder `.h` unless a C-only type from it appears in the header's signatures.
- Move includes only needed in `.cc` (e.g. `quantize.h` for `QuantizeMultiplier`)
  out of the `.h`.

## 9. Multi-input ops: requantize each input independently — never assume shared quant params

Sections 1–8 use single-data-input ops (HSwish, Softmax, Hardmax) as examples; their
single `input_scale` does not generalize to ops with **multiple data inputs** (e.g.
Select/Where's `x` and `y`, Concat, the arithmetic binaries).

Every input tensor and the output carry their **own** `(scale, zp)`, assigned
independently by the quantizer from each tensor's own value distribution — assume they
**differ**. Two failure modes both reduce to "assuming the quant params are equal":
collapsing all inputs onto one shared `in_scale`, or copying the selected int8 values
through byte-for-byte (which silently assumes `in_scale == out_scale` and equal
zero-points). Either looks correct only when the scales happen to coincide; once the
quantizer assigns different scales the output is wrong.

Requantize **each** input to the output's scale/zp using that input's **own** params:

```c
// per data input: use this input's own scale_in/zp_in -> output scale_out/zp_out
int32_t q_out = lrintf((float)(q_in - zp_in) * (scale_in / scale_out)) + zp_out;
q_out = MSMAX(MSMIN(q_out, 127), -128);
```

> **完整可抄的代码模板（.h/.c + runtime/opcoder 接线）见 `implementation-guide.md` ⑤‴——写这类算子的 int8 时直接照抄改名，不要凭本节公式自行重写。**

- **数据搬运 / 选择类算子(Select/Where/Concat/Slice/Gather/Pad/Tile…)不豁免。** 它们虽不做
  算术,量化器仍给**输出**分配独立的 `(scale, zp)`,通常 ≠ 输入的——所以"只是把值搬过去"也
  必须按源张量自己的 qparams 重量化到输出 qparams。**直接整型字节拷贝只在输入与输出 qparams
  实际相等时才成立,而这必须从生成代码核实,不能从规格推定**——源框架的量化 trait(如 TFLite
  `SameOperandsAndResultsScale`)约束的是源框架自家 converter,本仓库 `full_quant_quantizer`
  按各张量独立分配 qparams、不落实该类 trait,故 trait 不构成依据;不确定就重量化,别假设。
  失配的典型信号:生成代码里输入 `DoQuantize...(scale_a, zp_a)` 与输出
  `DoDequantize...(scale_b, zp_b)` 的 scale/zp 不同,却只做字节拷贝。
- **int8 计算函数的签名必须带量化参数。** 形如 `ElementXxxInt8(cond, x, y, out, num)`——**没有任何
  scale/zp 入参**——必然是字节拷贝,默认就是 bug。正确签名要带**各输入与输出各自的** `(scale, zp)`
  (或预算的定点乘数),并在循环里据此重量化。仅当该算子强制三方同 qparams 时才可省略量化参数,且
  **必须在函数注释里写明依据**(如"依赖转换器对本算子落实 SameOperandsAndResultsScale")。审查一个
  int8 计算函数,先看签名有没有量化参数——没有就先怀疑它漏了重量化。
- **int8/uint8 纯计算文件放 `nnacl_c/int8/xxx_int8.c` 或通用 `nnacl_c/base/xxx.c`,不要塞进 `nnacl_c/fp32/`。** fp32 目录只放真实 float 计算；原生整型-only 算子即使豁免量化，也不是 fp32 路径。
- Read each input's `quant_params().front()` separately; do not share `scale_in/zp_in`
  between inputs.
- Per §2/§2a, the **runtime int8 kernel and the opcoder must perform identical
  requantization**. The runtime kernel reads each input's real `Tensor::quant_params()`
  and applies the same formula — it must not take an identity-copy shortcut while the
  opcoder requantizes, or `bias_correction` and the generated MCU code will diverge.
- This bug only surfaces when the data inputs have **different value ranges** (hence
  different scales); the verification suite must include such a case — see hs-verify-op-host's
  case-design guidance for multi-input ops.
