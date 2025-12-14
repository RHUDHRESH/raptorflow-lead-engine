#!/usr/bin/env python3
"""
Raptorflow Lead Engine - Flight Check

Run lightweight diagnostics to confirm the local environment is ready before
starting the backend/frontend stack.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from typing import List, Tuple

# Ensure Windows consoles can emit UTF-8 characters without exploding
try:  # pragma: no cover - defensive on non-Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _run_command(cmd: List[str]) -> Tuple[bool, str]:
    """Run a command and return (success, output_or_error)."""
    run_cmd = cmd
    if os.name == "nt":
        # Ensure Windows resolves .cmd/.bat via the shell so npm.cmd etc. are found
        run_cmd = ["cmd", "/c"] + cmd
    try:
        result = subprocess.run(run_cmd, capture_output=True, text=True, check=True)
        return True, result.stdout.strip()
    except FileNotFoundError:
        return False, "command not found"
    except subprocess.CalledProcessError as exc:
        output = exc.stdout or exc.stderr or "unknown error"
        return False, output.strip()


def check_python() -> Tuple[bool, str]:
    ok = sys.version_info >= (3, 9)
    detail = f"{sys.version.split()[0]} (requires 3.9+)"
    return ok, detail


def check_node() -> Tuple[bool, str]:
    return _run_command(["node", "--version"])


def check_npm() -> Tuple[bool, str]:
    ok, detail = _run_command(["npm", "--version"])
    if not ok:
        detail += " (install Node.js or ensure npm.cmd is on PATH)"
    return ok, detail


def check_tesseract() -> Tuple[bool, str]:
    candidates = [
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for exe in [c for c in candidates if c and os.path.exists(c)]:
        ok, output = _run_command([exe, "--version"])
        if ok:
            first_line = output.splitlines()[0]
            return True, first_line if os.path.basename(exe) == "tesseract.exe" else f"{first_line} ({exe})"
    return False, "tesseract binary not found. Install from https://github.com/UB-Mannheim/tesseract/wiki and add it to PATH."


def check_ollama(base_url: str) -> Tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                models = ", ".join(m.get("name", "?") for m in data.get("models", [])) or "no models"
                return True, f"reachable ({models})"
            return False, f"HTTP {resp.status}"
    except urllib.error.URLError as exc:
        return False, f"unreachable ({exc.reason})"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"unreachable ({exc})"


def print_status(name: str, ok: bool, detail: str) -> None:
    symbol = "✅" if ok else "❌"
    print(f"{symbol} {name:<18} {detail}")


def main() -> int:
    print("🔎 Raptorflow Flight Check")
    print(f"   OS: {platform.system()} {platform.release()}")
    print(f"   Working Dir: {os.getcwd()}")
    print()

    failures = 0

    checks = [
        ("Python",) + check_python(),
        ("Node.js",) + check_node(),
        ("npm",) + check_npm(),
        ("Tesseract OCR",) + check_tesseract(),
        (
            "Ollama",
            *check_ollama(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
        ),
    ]

    for name, ok, detail in checks:
        print_status(name, ok, detail)
        if not ok:
            failures += 1

    print()
    if failures:
        print(f"❌ Flight check failed ({failures} issue{'s' if failures != 1 else ''} detected)")
        return 1

    print("✅ Flight check passed. You are ready for liftoff!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
