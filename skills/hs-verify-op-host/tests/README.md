# hs-verify-op-host self-tests

These hardware-free tests cover the inference harness and the training runner.
Inference tests load `../scripts/run_all_cases.py` directly and check its
classification, capability gates, output parsing, and configuration helpers.
Training tests cover locked case inputs, schema compatibility, expected
converter rejection, runner rules, and aggregation.

Run them from `skills/hs-verify-op-host`:

```bash
python3 -m pytest tests/ -v
```

The tests need Python, pytest, and numpy. They do not need MindSpore Lite,
`converter_lite`, or a board. Run them after changing either harness before
using it for a verdict.
