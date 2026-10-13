import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_manual_inputs.py"


def test_opdir_only_preflight_does_not_crash(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--opdir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    assert "Traceback" not in result.stderr
    assert "AttributeError" not in result.stderr
    assert "OP_MANUAL_INPUT_TIER=" in result.stdout
