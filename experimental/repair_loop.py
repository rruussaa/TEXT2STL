"""Repair loop for experimental CadQuery generation."""

from __future__ import annotations

from app.llm_client import LLMClient
from app.validator import validate_stl, validation_passed
from experimental.cadquery_agent import generate_cadquery_code, repair_cadquery_code
from experimental.quality import assess_code_quality
from experimental.sandbox_runner import run_cadquery_code
from experimental.templates import get_template_code

def _llm_error_message(exc: Exception) -> str:
    message = str(exc).replace("\r", " ").replace("\n", " ").strip()
    if len(message) > 500:
        message = message[:497] + "..."
    return (
        "LLM generation failed before CadQuery code was produced. "
        "If you are using Ollama, the local model may have run out of RAM/VRAM. "
        f"Details: {message}"
    )


def _run_attempt(
    user_prompt: str,
    code: str,
    output_path: str,
    attempt_index: int,
    timeout_sec: int,
    repair: bool = False,
    template: bool = False,
) -> tuple[dict, dict, bool]:
    run_result = run_cadquery_code(code, output_path, timeout_sec=timeout_sec)
    quality = {"ok": False, "issues": [], "template_name": None}
    validation = {}
    validation_ok = False
    if run_result.get("success"):
        quality = assess_code_quality(user_prompt, code)
        validation = validate_stl(run_result.get("output_path", output_path))
        validation_ok = validation_passed(validation)

    success = bool(run_result.get("success") and quality.get("ok") and validation_ok)
    traceback_text = run_result.get("traceback", "")
    if run_result.get("success") and not quality.get("ok"):
        traceback_text = "Quality check failed: " + "; ".join(quality.get("issues", []))
    elif run_result.get("success") and not validation_ok:
        warnings = "; ".join(validation.get("warnings", [])) or "STL validation failed"
        traceback_text = (
            "STL validation failed. "
            f"Warnings: {warnings}. "
            f"Bounds mm: {validation.get('bounds_mm')}. "
            f"Volume mm3: {validation.get('volume_mm3')}. "
            f"Watertight: {validation.get('is_watertight')}. "
            "Do not repeat the same geometry. Replace it with a single connected watertight solid. "
            "Make every unioned part overlap another part by at least 2 mm. "
            "Avoid separated or barely touching cylinders/spheres. "
            "For humans or characters, use a blocky torso with overlapping box limbs and an overlapping head."
        )

    attempt = {
        "attempt": attempt_index,
        "repair": repair,
        "template": template,
        "code": code,
        "success": success,
        "code_safe": bool(run_result.get("code_safe")),
        "safety_errors": run_result.get("safety_errors", []),
        "quality_ok": bool(quality.get("ok")),
        "quality_issues": quality.get("issues", []),
        "template_name": quality.get("template_name"),
        "validation_pass": validation_ok,
        "validation": validation,
        "traceback": traceback_text,
    }
    return attempt, run_result, success


def run_with_repair_loop(
    user_prompt: str,
    output_path: str,
    client: LLMClient,
    max_repairs: int = 2,
    timeout_sec: int = 10,
) -> dict:
    attempts: list[dict] = []
    template_code = get_template_code(user_prompt)
    if template_code:
        attempt, run_result, success = _run_attempt(
            user_prompt=user_prompt,
            code=template_code,
            output_path=output_path,
            attempt_index=0,
            timeout_sec=timeout_sec,
            repair=False,
            template=True,
        )
        attempts.append(attempt)
        if success:
            return {
                "success": True,
                "output_path": run_result.get("output_path", output_path),
                "code": template_code,
                "attempts": attempts,
                "repair_attempts": 0,
                "quality_issues": attempt.get("quality_issues", []),
                "template_fallback": True,
                "template_name": attempt.get("template_name"),
            }

    try:
        code = generate_cadquery_code(user_prompt, client)
    except Exception as exc:
        error = _llm_error_message(exc)
        return {
            "success": False,
            "output_path": output_path,
            "code": "",
            "attempts": [
                {
                    "attempt": 0,
                    "repair": False,
                    "template": False,
                    "code": "",
                    "success": False,
                    "code_safe": False,
                    "safety_errors": [],
                    "quality_ok": False,
                    "quality_issues": [],
                    "template_name": None,
                    "validation_pass": False,
                    "validation": {},
                    "traceback": error,
                }
            ],
            "repair_attempts": 0,
            "quality_issues": [],
            "template_fallback": False,
            "error": error,
        }
    for attempt_index in range(max_repairs + 1):
        attempt, run_result, success = _run_attempt(
            user_prompt=user_prompt,
            code=code,
            output_path=output_path,
            attempt_index=attempt_index,
            timeout_sec=timeout_sec,
            repair=attempt_index > 0,
        )
        attempts.append(attempt)

        if success:
            return {
                "success": True,
                "output_path": run_result.get("output_path", output_path),
                "code": code,
                "attempts": attempts,
                "repair_attempts": attempt_index,
                "quality_issues": [],
                "template_fallback": False,
            }

        if attempt.get("quality_issues") and get_template_code(user_prompt):
            break

        if attempt_index >= max_repairs:
            break

        traceback_text = attempt.get("traceback") or run_result.get("traceback") or "Unknown CadQuery error."
        try:
            code = repair_cadquery_code(user_prompt, traceback_text, code, client)
        except Exception as exc:
            attempts.append(
                {
                    "attempt": attempt_index + 1,
                    "repair": True,
                    "template": False,
                    "code": "",
                    "success": False,
                    "code_safe": False,
                    "safety_errors": [],
                    "quality_ok": False,
                    "quality_issues": [],
                    "template_name": None,
                    "validation_pass": False,
                    "validation": {},
                    "traceback": _llm_error_message(exc),
                }
            )
            break
    template_code = get_template_code(user_prompt)
    if template_code and template_code.strip() != code.strip():
        attempt, run_result, success = _run_attempt(
            user_prompt=user_prompt,
            code=template_code,
            output_path=output_path,
            attempt_index=len(attempts),
            timeout_sec=timeout_sec,
            repair=False,
            template=True,
        )
        attempts.append(attempt)
        if success:
            return {
                "success": True,
                "output_path": run_result.get("output_path", output_path),
                "code": template_code,
                "attempts": attempts,
                "repair_attempts": max(0, len([a for a in attempts if a.get("repair")]) ),
                "quality_issues": attempt.get("quality_issues", []),
                "template_fallback": True,
                "template_name": attempt.get("template_name"),
            }

    return {
        "success": False,
        "output_path": output_path,
        "code": code,
        "attempts": attempts,
        "repair_attempts": max(0, len([a for a in attempts if a.get("repair")]) ),
        "quality_issues": attempts[-1].get("quality_issues", []) if attempts else [],
        "template_fallback": False,
        "error": attempts[-1].get("traceback", "Experimental generation failed.") if attempts else "Experimental generation failed.",
    }


