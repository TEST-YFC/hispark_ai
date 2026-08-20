import importlib.util
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
