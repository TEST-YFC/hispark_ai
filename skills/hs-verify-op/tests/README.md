# hs-verify-op harness self-tests

Hardware-free unit tests for the **fixed harness** (`../scripts/run_all_cases.py`).

`run_all_cases.py` is immutable infrastructure shared by every operator. The one
sanctioned reason to edit it (a genuine capability gap) is also the one chance to
silently break the functions that keep the verdict honest — and that failure mode
turns red into green without anyone noticing. These tests pin those functions so a
maintenance edit fails **loudly here** instead of fabricating PASSes on real runs.

What's covered (all by loading the real module by path, so the tests stay coupled to
its actual signatures):

- **`cosine_similarity`** — the crown jewel: both-zero→1.0, exactly-one-zero→0.0
  (the laundering trap), never NaN/Inf, scale-invariance, flatten.
- **`assert_int8_genuine`** — INT8_NOT_GENUINE gate (symbol called vs merely mentioned,
  custom symbol, list, disabled, no codegen).
- **`check_case_regression`** — CASES_REDUCED gate (shrink w/o ACK exits, with ACK traces).
- **`validate_checklist_refs` / `report_capability_coverage`** — capability-checklist gates.
- **`parse_benchmark_outputs`**, **`_err_msg`** (crash/timeout classification), **`make_cfg`**.

## Run

```bash
cd <skill>/hs-verify-op
python3 -m pytest tests/ -v
```

Needs only `numpy` + `pytest` (no MSLite, no converter_lite, no board). Run it before
sign-off on **any** change to `run_all_cases.py`; it must stay 100% green.
