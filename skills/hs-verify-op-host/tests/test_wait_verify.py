import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


WAIT = Path(__file__).resolve().parent.parent / "scripts" / "wait_verify.sh"


@pytest.mark.skipif(os.name == "nt", reason="wait_verify.sh is exercised in Linux/WSL")
def test_waiter_allows_run_id_startup_race(tmp_path):
    log = tmp_path / "verify.log"
    log.write_text("", encoding="utf-8")
    writer = subprocess.Popen([
        sys.executable,
        "-c",
        (
            "import pathlib,time; time.sleep(0.2); "
            f"pathlib.Path({str(log)!r}).write_text("
            "'RUN_ID=race-test\\nVERDICT: 1 PASS / 0 FAIL\\nHARNESS_EXIT=0\\n', "
            "encoding='utf-8')"
        ),
    ])
    try:
        completed = subprocess.run(
            ["bash", str(WAIT), str(log), "3", str(writer.pid), "race-test"],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    finally:
        writer.wait(timeout=5)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "TERMINAL=race-test:SUCCESS" in completed.stdout
