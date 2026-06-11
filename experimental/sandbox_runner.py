"""Subprocess runner for experimental CadQuery code."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.safety import check_code_safety


SANDBOX_SCRIPT = r"""
import builtins
import json
import pathlib
import traceback
import sys

SAFE_BUILTIN_NAMES = [
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int",
    "len", "list", "max", "min", "range", "round", "set", "sum",
    "tuple", "zip"
]
ALLOWED_IMPORTS = {"cadquery", "math"}


def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".")[0]
    if root not in ALLOWED_IMPORTS:
        raise ImportError(f"Import is not allowed: {name}")
    return builtins.__import__(name, globals, locals, fromlist, level)


def main():
    payload = json.loads(sys.stdin.read())
    code = payload["code"]
    output_path = payload["output_path"]
    safe_builtins = {name: getattr(builtins, name) for name in SAFE_BUILTIN_NAMES}
    safe_builtins["__import__"] = safe_import
    namespace = {"__builtins__": safe_builtins}

    try:
        exec(compile(code, "<generated_cadquery>", "exec"), namespace, namespace)
        build_model = namespace.get("build_model")
        if not callable(build_model):
            raise ValueError("Generated code did not define build_model().")

        model = build_model()
        import cadquery as cq
        cq.exporters.export(model, output_path)
        exported = pathlib.Path(output_path)
        if not exported.exists() or exported.stat().st_size <= 0:
            raise RuntimeError("CadQuery export did not create a non-empty STL file.")
        print(json.dumps({"success": True, "output_path": output_path}))
    except Exception:
        print(json.dumps({"success": False, "traceback": traceback.format_exc()}))


if __name__ == "__main__":
    main()
"""


def run_cadquery_code(code: str, output_path: str, timeout_sec: int = 10) -> dict:
    safety = check_code_safety(code)
    if not safety["safe"]:
        return {
            "success": False,
            "code_safe": False,
            "safety_errors": safety["errors"],
            "traceback": "Safety check failed: " + "; ".join(safety["errors"]),
            "output_path": output_path,
        }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    payload = json.dumps({"code": code, "output_path": output_path})
    try:
        completed = subprocess.run(
            [sys.executable, "-c", SANDBOX_SCRIPT],
            input=payload,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "code_safe": True,
            "safety_errors": [],
            "traceback": f"Sandbox timed out after {timeout_sec} seconds.",
            "output_path": output_path,
        }

    parsed = None
    for line in reversed(completed.stdout.strip().splitlines()):
        try:
            parsed = json.loads(line)
            break
        except json.JSONDecodeError:
            continue

    if parsed is None:
        return {
            "success": False,
            "code_safe": True,
            "safety_errors": [],
            "traceback": completed.stderr or completed.stdout or "Sandbox produced no parseable result.",
            "output_path": output_path,
        }

    parsed.setdefault("success", False)
    parsed["code_safe"] = True
    parsed["safety_errors"] = []
    parsed.setdefault("traceback", completed.stderr)
    parsed.setdefault("output_path", output_path)
    return parsed
