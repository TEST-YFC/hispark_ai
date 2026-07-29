# Optimizer Fusion Pass Template

Read this when **decision3 (③ 需要融合 pass)** identified that the source framework expresses your operator
as a composite subgraph (HardSwish-as-Div/Mul/Relu6/Add, Swish-as-Sigmoid/Mul, GeLU, Mish,
LayerNorm variants, etc.) and **no existing fusion pass** in `tools/optimizer/fusion/`
already handles it.

Canonical example to copy from: `tools/optimizer/fusion/hard_swish_fusion.cc`
(matches `Div(Mul(x, Relu6(Add(x, 3))), 6)` → `Activation(HSWISH)`).

---

## Files to create

### `tools/optimizer/fusion/xxx_fusion.h`

```cpp
/**
 * Copyright <current_year> Huawei Technologies Co., Ltd
 * ... Apache-2.0 header ...
 */
#ifndef MINDSPORE_LITE_TOOLS_OPTIMIZER_FUSION_XXX_FUSION_H_
#define MINDSPORE_LITE_TOOLS_OPTIMIZER_FUSION_XXX_FUSION_H_

#include <memory>
#include <string>
#include "schema/inner/model_generated.h"
#include "tools/optimizer/common/pattern_process_pass_extends.h"
#include "include/utils/utils.h"
#include "tools/optimizer/common/gllo_utils.h"

namespace mindspore::opt {
class XxxFusion : public LitePatternProcessPass {
 public:
  explicit XxxFusion(const std::string &name = "XxxFusion", bool multigraph = true)
      : LitePatternProcessPass(name, multigraph) {}
  ~XxxFusion() override = default;

 private:
  bool Init() const;
  bool CheckPattern(const EquivPtr &equiv) const;
  const BaseRef DefinePattern() const override;
  const AnfNodePtr Process(const FuncGraphPtr &, const AnfNodePtr &, const EquivPtr &) const override;

 protected:
  // One VarPtr per node you want to capture from the matched subgraph.
  // `mutable` because DefinePattern() is const but needs to initialize these.
  mutable VarPtr input_ = nullptr;
  mutable VarPtr some_const_ = nullptr;
};
}  // namespace mindspore::opt
#endif
```

### `tools/optimizer/fusion/xxx_fusion.cc`

Three methods you implement:

**`DefinePattern()`** — build a `VectorRef` tree describing the subgraph to match.
Each level is `VectorRef({op_predicate, input1, input2, ...})`. Use
`std::make_shared<CondVar>(IsSpecifiedNode<&prim::kPrimXxx>)` to constrain a node
to a specific primitive type, or `std::make_shared<Var>()` (stored in a member
`VarPtr`) to capture an arbitrary node by name.

**`Process()`** — runs on each match. Validate via `CheckPattern()`, then build
the replacement node with `func_graph->NewCNode(new_inputs)` and return it. The
returned node replaces the *outermost* (root) node of the matched pattern.

**`CheckPattern()`** — verify constant values, shapes, or dtypes that the structural
pattern can't express (e.g. "the Add constant must be exactly 3.0"). Return false
to reject the match.

Refer to `hard_swish_fusion.cc` line-by-line — the structure of `DefinePattern()`
and the AnfNode → CNode → Parameter → tensor traversal in `CheckPattern()` are
the parts most easily copied wrong.

---

## Registration

Add the pass to `tools/converter/anf_transform.cc::InitFusions()`:

```cpp
std::vector<opt::PassPtr> fusions{
  // ... existing passes ...
  std::make_shared<opt::XxxFusion>(),
};
```

**Order matters.** Place the new pass *before* any pass that would consume its
output. When in doubt, put it near related fusions — for example, activation-
producing fusions (`HardSwishFusion`, `SigmoidMulFusion` → Swish) live together
near the top of the list, before `ConvActivationFusion` which expects an already-
fused activation node.

---

## Verification

After rebuilding `converter_lite`:

1. Convert a model containing the composite subgraph.
2. Inspect the converted output graph to confirm the fusion fired and the
   replacement node appears in place of the composite.
3. Run accuracy verification via the `hs-debug-op-host-accuracy` skill (or the repo-native
   `converter_lite` + `benchmark`); if your fusion semantics are wrong, the
   cosine-similarity check fails. Remember the produced primitive still needs its
   full ②–⑦ pathway — the fusion alone does not make it convert/compute.

---

## Other useful references

- `tools/optimizer/fusion/sigmoid_mul_fusion.cc` — Swish (Sigmoid + Mul) → `Activation(SWISH)`
- `tools/optimizer/fusion/activation_fusion.cc` — generic activation-merging logic
- `tools/optimizer/common/pattern_process_pass_extends.h` — base class `LitePatternProcessPass`
- `tools/optimizer/common/gllo_utils.h` — helper predicates like `IsSpecifiedNode`
