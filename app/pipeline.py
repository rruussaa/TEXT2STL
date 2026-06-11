"""High-level stable and experimental generation pipelines."""

from __future__ import annotations

import json
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.llm_client import LLMClient
from app.schemas import model_to_dict, validate_name_plate_spec
from app.safety import check_code_safety
from app.validator import validate_stl
from experimental.local_fallback import cadquery_available, generate_local_experimental_stl
from experimental.repair_loop import run_with_repair_loop
from generators.name_plate import generate_name_plate


def _safe_slug(value: str, fallback: str = "model") -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())[:40].strip("_")
    return slug or fallback


def make_output_path(prefix: str, output_dir: Path | None = None) -> str:
    settings = get_settings()
    directory = output_dir or settings.output_dir
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    name = f"{_safe_slug(prefix)}_{stamp}_{uuid4().hex[:8]}.stl"
    return str(directory / name)


def parse_json_response(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def validation_passed(report: dict) -> bool:
    return bool(
        report.get("file_exists")
        and report.get("file_size_bytes", 0) > 0
        and report.get("triangle_count", 0) > 0
        and report.get("volume_mm3", 0) > 0
        and report.get("fits_printer")
        and not report.get("warnings")
    )


def run_stable_pipeline(
    user_prompt: str,
    output_path: str | None = None,
    client: LLMClient | None = None,
) -> dict:
    client = client or LLMClient.from_env()
    result = {
        "mode": "stable",
        "prompt": user_prompt,
        "success": False,
        "json_valid": False,
        "stl_generated": False,
        "validation_pass": False,
        "raw_json": "",
        "spec": None,
        "output_path": output_path,
        "validation": {},
        "error": "",
    }

    try:
        raw_json = client.stable_json(user_prompt)
        result["raw_json"] = raw_json
        spec_data = parse_json_response(raw_json)
        spec = validate_name_plate_spec(spec_data)
        result["json_valid"] = True
        result["spec"] = model_to_dict(spec)

        output_path = output_path or make_output_path(f"name_plate_{spec.text}")
        result["output_path"] = output_path
        generate_name_plate(spec, output_path)
        result["stl_generated"] = Path(output_path).exists()
        validation = validate_stl(output_path)
        result["validation"] = validation
        result["validation_pass"] = validation_passed(validation)
        result["success"] = bool(result["stl_generated"] and result["validation_pass"])
        return result
    except Exception:
        result["error"] = traceback.format_exc()
        return result


def run_experimental_pipeline(
    user_prompt: str,
    output_path: str | None = None,
    client: LLMClient | None = None,
    max_repairs: int = 2,
) -> dict:
    client = client or LLMClient.from_env()
    output_path = output_path or make_output_path("experimental")
    result = {
        "mode": "experimental",
        "prompt": user_prompt,
        "success": False,
        "code_generated": False,
        "code_safe": False,
        "stl_generated": False,
        "validation_pass": False,
        "repair_attempts": 0,
        "code": "",
        "attempts": [],
        "output_path": output_path,
        "validation": {},
        "error": "",
    }

    try:
        if client.settings.llm_mode == "mock" and not cadquery_available():
            code = client.experimental_code(user_prompt)
            safety = check_code_safety(code)
            generate_local_experimental_stl(user_prompt, output_path)
            validation = validate_stl(output_path)
            result.update(
                {
                    "success": validation_passed(validation),
                    "code": code,
                    "code_generated": bool(code.strip()),
                    "code_safe": bool(safety["safe"]),
                    "stl_generated": Path(output_path).exists(),
                    "validation": validation,
                    "validation_pass": validation_passed(validation),
                    "local_fallback": True,
                    "attempts": [
                        {
                            "attempt": 0,
                            "repair": False,
                            "code": code,
                            "success": validation_passed(validation),
                            "code_safe": bool(safety["safe"]),
                            "safety_errors": safety["errors"],
                            "traceback": (
                                "CadQuery is not installed in this local Python environment. "
                                "Generated code was safety-checked, then a local demo STL fallback was exported. "
                                "Use Docker/conda for full experimental CadQuery execution."
                            ),
                        }
                    ],
                }
            )
            return result

        run_result = run_with_repair_loop(
            user_prompt=user_prompt,
            output_path=output_path,
            client=client,
            max_repairs=max_repairs,
        )
        result["code"] = run_result.get("code", "")
        result["code_generated"] = bool(result["code"].strip())
        result["attempts"] = run_result.get("attempts", [])
        result["repair_attempts"] = run_result.get("repair_attempts", 0)
        result["code_safe"] = bool(result["attempts"] and result["attempts"][-1].get("code_safe"))
        result["error"] = run_result.get("error", "")
        result["quality_issues"] = run_result.get("quality_issues", [])
        result["template_fallback"] = bool(run_result.get("template_fallback"))
        result["template_name"] = run_result.get("template_name", "")
        result["success"] = bool(run_result.get("success"))
        result["stl_generated"] = Path(output_path).exists()

        if result["stl_generated"]:
            validation = validate_stl(output_path)
            result["validation"] = validation
            result["validation_pass"] = validation_passed(validation)
            result["success"] = bool(result["success"] and result["validation_pass"])
        return result
    except Exception:
        result["error"] = traceback.format_exc()
        return result


