#!/usr/bin/env python3
"""Cross-check serial-port visibility before a board run.

This is deliberately an inventory tool, not a flasher.  On Windows it queries
independent sources because Win32_SerialPort/WMI can omit USB UARTs such as
CH340.  A probe receipt is useful evidence for routing, but a device name by
itself is never proof that a port is the WS63 board.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PORT_RE = re.compile(r"\b(COM\d+)\b", re.IGNORECASE)
USB_UART_RE = re.compile(
    r"ch34[01]|ch340|ch341|usb[- ]serial|cp210|ftdi|usb uart|silicon labs|prolific",
    re.IGNORECASE,
)
INTERNAL_RE = re.compile(
    r"intel.*(?:amt|active management technology)|(?:amt|active management technology).*sol|bluetooth",
    re.IGNORECASE,
)


def _powershell(command: str, timeout: float) -> tuple[str, str | None]:
    """Run a bounded PowerShell query; return stdout and an error label."""
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return "", type(exc).__name__
    if completed.returncode != 0:
        return completed.stdout, f"rc={completed.returncode}: {completed.stderr.strip()}"
    return completed.stdout, None


def _ports(text: str) -> list[str]:
    return sorted({m.upper() for m in PORT_RE.findall(text)}, key=lambda p: int(p[3:]))


def parse_dotnet_ports(text: str) -> list[str]:
    return _ports(text)


def parse_registry(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = re.search(r"Serial\d+\s*[:=]\s*(COM\d+)", line, re.IGNORECASE)
        if match:
            result[match.group(1).upper()] = line.strip()
    return result


def parse_pnp(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    # pnputil prints one device per blank-line-delimited block.  Keep the
    # whole block for a port so Instance ID/VID/PID lines adjacent to the
    # Device Description remain associated with that COM port.
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    for block in blocks:
        ports = _ports(block)
        if not ports:
            continue
        evidence = [line.strip() for line in block.splitlines() if line.strip()]
        for port in ports:
            result.setdefault(port, []).extend(evidence)
    return result


def classify(port: str, evidence: list[str]) -> str:
    joined = " ".join(evidence)
    if INTERNAL_RE.search(joined):
        return "internal_or_virtual"
    if USB_UART_RE.search(joined):
        return "usb_uart_candidate"
    return "unknown_candidate"


def inventory(timeout: float = 8.0) -> dict[str, Any]:
    system = platform.system()
    sources: dict[str, Any] = {}
    by_port: dict[str, list[str]] = {}

    if system == "Windows":
        dotnet, err = _powershell(
            "[System.IO.Ports.SerialPort]::GetPortNames() | ConvertTo-Json -Compress",
            timeout,
        )
        sources["dotnet"] = {"ports": parse_dotnet_ports(dotnet), "error": err}
        for port in sources["dotnet"]["ports"]:
            by_port.setdefault(port, []).append(".NET SerialPort.GetPortNames")

        registry, err = _powershell(
            "Get-ItemProperty 'HKLM:\\HARDWARE\\DEVICEMAP\\SERIALCOMM' | Format-List",
            timeout,
        )
        registry_map = parse_registry(registry)
        sources["registry"] = {"ports": sorted(registry_map), "error": err}
        for port, line in registry_map.items():
            by_port.setdefault(port, []).append(f"registry: {line}")

        # Get-PnpDevice may block on broken drivers; pnputil is optional and bounded.
        pnp, err = _powershell(
            "pnputil /enum-devices /class Ports /connected 2>$null",
            timeout,
        )
        pnp_map = parse_pnp(pnp)
        sources["pnputil"] = {
            "ports": sorted(pnp_map),
            "error": err,
            # Keep bounded raw evidence so VID/PID or hardware IDs on a line
            # adjacent to the COM description remain traceable.
            "raw_excerpt": pnp[:12000],
        }
        for port, lines in pnp_map.items():
            by_port.setdefault(port, []).extend(f"pnputil: {line}" for line in lines)
    else:
        paths: list[str] = []
        for root in ("/dev/serial/by-id", "/dev/serial/by-path"):
            if os.path.isdir(root):
                paths.extend(str(p) for p in Path(root).iterdir())
        paths.extend(str(p) for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*") for p in Path("/dev").glob(pattern[5:]))
        sources["linux-dev"] = {"paths": sorted(set(paths)), "error": None}
        for path in paths:
            by_port.setdefault(path, []).append(path)

    candidates = []
    for port in sorted(by_port):
        evidence = by_port[port]
        candidates.append({"port": port, "class": classify(port, evidence), "evidence": evidence})
    compatible = [item for item in candidates if item["class"] == "usb_uart_candidate"]
    return {
        "schema_version": 1,
        "probed_at_utc": datetime.now(timezone.utc).isoformat(),
        "system": system,
        "sources": sources,
        "ports": candidates,
        "compatible_candidates": compatible,
        "unique_compatible": len(compatible) == 1,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-check serial-port visibility")
    parser.add_argument("--output", type=Path, help="write the JSON probe receipt")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args(argv)
    report = inventory(args.timeout)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SERIAL_PROBE system={report['system']} ports={len(report['ports'])} compatible={len(report['compatible_candidates'])}")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
