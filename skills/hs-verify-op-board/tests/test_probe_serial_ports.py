import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "probe_serial_ports.py"
spec = importlib.util.spec_from_file_location("probe_serial_ports", SCRIPT)
probe = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(probe)


def test_dotnet_and_registry_find_port_omitted_by_wmi():
    assert probe.parse_dotnet_ports('["COM3","COM12"]') == ["COM3", "COM12"]
    registry = "\\Device\\Serial0 : COM3\n\\Device\\Serial2 : COM12\n"
    assert sorted(probe.parse_registry(registry)) == ["COM12", "COM3"]


def test_usb_uart_is_preferred_over_internal_amt_sol():
    assert probe.classify("COM3", ["Intel Active Management Technology - SOL"]) == "internal_or_virtual"
    assert probe.classify("COM12", ["USB-SERIAL CH340 (COM12)", "VID_1A86&PID_7523"]) == "usb_uart_candidate"


def test_pnp_parser_keeps_device_evidence():
    parsed = probe.parse_pnp(
        "Instance ID: USB\\VID_1A86&PID_7523\\X\n"
        "Device Description: USB-SERIAL CH340 (COM12)\n"
        "Status: Started\n"
    )
    assert "Instance ID: USB\\VID_1A86&PID_7523\\X" in parsed["COM12"]
    assert "Device Description: USB-SERIAL CH340 (COM12)" in parsed["COM12"]


def test_probe_retries_after_empty_inventory(monkeypatch):
    empty = {
        "schema_version": 1,
        "probed_at_utc": "t0",
        "system": "Windows",
        "sources": {},
        "ports": [],
        "compatible_candidates": [],
        "unique_compatible": False,
    }
    ready = {
        "schema_version": 1,
        "probed_at_utc": "t1",
        "system": "Windows",
        "sources": {},
        "ports": [{"port": "COM12", "class": "usb_uart_candidate", "evidence": ["CH340"]}],
        "compatible_candidates": [{"port": "COM12", "class": "usb_uart_candidate", "evidence": ["CH340"]}],
        "unique_compatible": True,
    }
    reports = iter((empty, ready))
    monkeypatch.setattr(probe, "inventory", lambda timeout, target="auto": next(reports))
    monkeypatch.setattr(probe.time, "sleep", lambda seconds: None)

    result = probe.probe_with_retries(timeout=1, attempts=3, interval=2)

    assert result["unique_compatible"] is True
    assert result["attempt_count"] == 2
    assert len(result["attempt_history"]) == 2
    assert result["attempt_history"][0]["probe_attempt"] == 1
    assert result["attempt_history"][1]["probe_attempt"] == 2


def test_decode_output_handles_utf16_and_code_page_text():
    text = "设备描述: USB-SERIAL CH340 (COM12)"
    assert "COM12" in probe._decode_output(text.encode("utf-16"))
    assert "COM12" in probe._decode_output(text.encode("gb18030"))


def test_cli_writes_receipt_and_leaves_json_as_last_output_line(monkeypatch, tmp_path, capsys):
    report = {
        "schema_version": 1,
        "probed_at_utc": "2026-01-01T00:00:00Z",
        "system": "Windows",
        "sources": {},
        "ports": [],
        "compatible_candidates": [],
        "unique_compatible": False,
        "attempt_count": 1,
        "attempts_requested": 1,
        "retry_interval_seconds": 0.0,
        "attempt_history": [],
    }
    monkeypatch.setattr(probe, "probe_with_retries", lambda timeout, attempts, interval, target="local": report)
    output = tmp_path / "serial_probe.json"

    assert probe.main(["--output", str(output), "--attempts", "1", "--interval", "0"]) == 0

    captured = capsys.readouterr().out.splitlines()
    assert json.loads(captured[-1]) == report
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_inventory_uses_windows_powershell_and_local_devices_from_wsl(monkeypatch):
    def fake_powershell(command, timeout):
        assert "SerialPort" in command or "SERIALCOMM" in command or "pnputil" in command
        if "SerialPort" in command:
            return '["COM12"]', None
        if "SERIALCOMM" in command:
            return "\\Device\\Serial1 : COM12", None
        return "Device Description: USB-SERIAL CH340 (COM12)", None

    monkeypatch.setattr(probe.platform, "system", lambda: "Linux")
    monkeypatch.setattr(probe.shutil, "which", lambda name: "powershell.exe" if name == "powershell.exe" else None)
    monkeypatch.setattr(probe, "_powershell", fake_powershell)

    result = probe.inventory(timeout=1, target="auto")

    assert result["probe_target"] == "windows+local"
    assert result["windows_interop"] is True
    assert result["unique_compatible"] is True
    assert result["compatible_candidates"][0]["port"] == "COM12"
