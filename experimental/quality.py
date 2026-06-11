"""Lightweight semantic quality checks for generated CadQuery code."""

from __future__ import annotations

import re

from experimental.templates import detect_template_name


FEATURE_GROUPS = {
    "airplane": [("fuselage", "body"), ("wing",), ("tail",), ("nose",)],
    "car": [("body",), ("cabin", "roof"), ("wheel",)],
    "chair": [("seat",), ("back", "backrest"), ("leg",)],
    "table": [("top", "tabletop"), ("leg",)],
    "rocket": [("body",), ("nose", "cone"), ("fin",)],
    "pyramid": [("egyptian_pyramid", "pyramid"), ("base", "plinth"), ("loft", "rect")],
    "house": [("base", "wall", "body"), ("roof",), ("door",), ("window",)],
    "robot": [("body",), ("head",), ("arm",), ("leg",)],
    "boat": [("hull",), ("cabin", "mast", "sail")],
    "vase": [("profile", "revolve", "outer"), ("neck", "hollow", "inner", "revolve")],
    "adult_novelty": [("shaft", "profile", "revolve"), ("base_flange", "flange", "base"), ("rounded_tip", "tip")],
    "pencil_holder": [("hole",), ("pushpoints", "points"), ("base", "body")],
    "open_box": [("outer",), ("inner", "cut"), ("wall", "box")],
    "phone_stand": [("base",), ("back",), ("lip",)],
    "cube_hole": [("box", "cube"), ("hole", "cut")],
}

PRIMITIVE_WORDS = {
    "cube",
    "box",
    "cylinder",
    "sphere",
    "ball",
    "cone",
    "ring",
    "washer",
    "tube",
}


def _normalized_code(code: str) -> str:
    return re.sub(r"[^a-z0-9_]+", " ", code.lower())


def _looks_like_generic_primitive(user_prompt: str, code: str) -> bool:
    prompt_words = set(re.findall(r"[a-z]+", user_prompt.lower()))
    primitive_request = bool(prompt_words & PRIMITIVE_WORDS) and len(prompt_words - PRIMITIVE_WORDS - {"make", "a", "an", "simple", "small", "with", "mm", "the", "center", "through"}) <= 3
    if primitive_request:
        return False

    lowered = code.lower()
    workplanes = lowered.count("cq.workplane") + lowered.count("workplane(")
    has_composition = ".union(" in lowered or ".cut(" in lowered or "pushpoints" in lowered or ".loft(" in lowered or ".revolve(" in lowered
    return workplanes <= 2 and not has_composition


def assess_code_quality(user_prompt: str, code: str) -> dict:
    issues: list[str] = []
    template_name = detect_template_name(user_prompt)
    normalized = _normalized_code(code)

    if template_name and template_name in FEATURE_GROUPS:
        for group in FEATURE_GROUPS[template_name]:
            if not any(token in normalized for token in group):
                issues.append(f"Missing recognizable {template_name} feature: {'/'.join(group)}")

    if _looks_like_generic_primitive(user_prompt, code):
        issues.append("Generated code looks like a generic primitive, not a part-based model.")

    return {
        "ok": not issues,
        "issues": issues,
        "template_name": template_name,
    }
