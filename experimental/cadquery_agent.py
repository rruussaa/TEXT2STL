"""Code generation helpers for experimental CadQuery mode."""

from __future__ import annotations

from app.llm_client import LLMClient, strip_code_fences


def generate_cadquery_code(user_prompt: str, client: LLMClient) -> str:
    return strip_code_fences(client.experimental_code(user_prompt))


def repair_cadquery_code(
    user_prompt: str,
    traceback_text: str,
    previous_code: str,
    client: LLMClient,
) -> str:
    return strip_code_fences(client.repair_code(user_prompt, traceback_text, previous_code))

