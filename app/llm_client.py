"""OpenAI-compatible and mock LLM client."""

from __future__ import annotations

import json
import re
import ast
from dataclasses import dataclass

from app.config import Settings, get_settings, read_prompt


COMPACT_GENERATION_INSTRUCTIONS = """

Compact generation:
- Keep the code compact: no more than 80 lines.
- For complex landmarks or organic objects, make a simplified, recognizable part-based approximation.
- Prefer a successful simple STL over intricate geometry that may fail.
- For humans, animals, or characters, use connected overlapping blocky parts instead of separated cylinders/spheres.
"""


@dataclass
class LLMClient:
    settings: Settings

    @classmethod
    def from_env(cls) -> "LLMClient":
        return cls(get_settings())

    def stable_json(self, user_prompt: str) -> str:
        if self.settings.llm_mode == "mock":
            return mock_stable_json(user_prompt)
        system_prompt = read_prompt("stable_json_prompt.md")
        return self._complete(system_prompt, user_prompt, max_tokens=180)

    def experimental_code(self, user_prompt: str) -> str:
        if self.settings.llm_mode == "mock":
            return mock_experimental_code(user_prompt)
        system_prompt = read_prompt("experimental_cadquery_prompt.md")
        if self.settings.llm_compact_generation:
            system_prompt += COMPACT_GENERATION_INSTRUCTIONS
        return strip_code_fences(
            self._complete(
                system_prompt,
                user_prompt,
                max_tokens=self.settings.llm_experimental_max_tokens,
            )
        )

    def repair_code(self, user_prompt: str, traceback_text: str, previous_code: str) -> str:
        if self.settings.llm_mode == "mock":
            return mock_repair_code(user_prompt)
        system_prompt = read_prompt("repair_prompt.md").format(
            user_prompt=user_prompt,
            traceback=traceback_text,
        )
        user_message = "Previous code:\n" + previous_code
        return strip_code_fences(
            self._complete(
                system_prompt,
                user_message,
                max_tokens=self.settings.llm_repair_max_tokens,
            )
        )

    def _complete(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        if self.settings.llm_mode != "openai_compatible":
            raise ValueError(f"Unsupported LLM_MODE: {self.settings.llm_mode}")

        from openai import OpenAI

        client = OpenAI(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout_sec,
        )
        response = client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        return content.strip()


def strip_code_fences(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    fenced_blocks = re.findall(r"```(?:[a-zA-Z0-9_+-]+)?\s*(.*?)```", cleaned, flags=re.DOTALL)
    candidates = sorted(fenced_blocks, key=lambda block: "def build_model" not in block)
    candidates.append(cleaned)

    for candidate in candidates:
        extracted = _extract_parseable_python(candidate)
        if extracted:
            return extracted
    return cleaned.strip()


def _extract_parseable_python(text: str) -> str:
    lines = text.strip().splitlines()
    start_indexes = [0]
    start_indexes.extend(
        index
        for index, line in enumerate(lines)
        if re.match(r"^\s*(?:def|import|from)\s+", line)
    )

    for start_index in dict.fromkeys(start_indexes):
        candidate_lines = lines[start_index:]
        for end_index in range(len(candidate_lines), 0, -1):
            candidate = "\n".join(candidate_lines[:end_index]).strip()
            if not candidate:
                continue
            try:
                tree = ast.parse(candidate)
            except SyntaxError:
                continue
            if any(isinstance(node, ast.FunctionDef) and node.name == "build_model" for node in tree.body):
                return candidate
    return ""


def _extract_dimensions(prompt: str) -> tuple[float, float]:
    normalized = prompt.lower().replace("*", "x").replace(" by ", " x ")

    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:x|by)\s*(\d+(?:[.,]\d+)?)", normalized)
    if match:
        return float(match.group(1).replace(",", ".")), float(match.group(2).replace(",", "."))

    width_match = re.search(r"(?:width|wide)\D{0,12}(\d+(?:[.,]\d+)?)", normalized)
    height_match = re.search(r"(?:height|tall|high)\D{0,12}(\d+(?:[.,]\d+)?)", normalized)
    if width_match and height_match:
        return float(width_match.group(1).replace(",", ".")), float(height_match.group(1).replace(",", "."))

    return 100.0, 35.0


def _extract_thickness(prompt: str) -> float:
    normalized = prompt.lower()
    match = re.search(r"(?:thick|thickness|deep)\D{0,12}(\d+(?:[.,]\d+)?)", normalized)
    if match:
        return float(match.group(1).replace(",", "."))
    return 3.0


def _clean_label_text(value: str) -> str:
    value = value.strip(" '\".,;:")
    value = re.split(
        r"\s+(?:thick|thickness|with|holes?|screw|rounded|corner|corners|width|height|wide|tall|high)\b",
        value,
        flags=re.IGNORECASE,
    )[0]
    value = re.sub(r"\s+", " ", value).strip(" -_.,;:")
    return value[:40] or "AI LAB"


def _extract_text(prompt: str) -> str:
    quoted = re.search(r"['\"]([^'\"]{1,40})['\"]", prompt)
    if quoted:
        return _clean_label_text(quoted.group(1))

    match = re.search(r"(?:text|says|say|label|wording)\s+(?:is\s+)?['\"]?([^,.;]+)", prompt, flags=re.IGNORECASE)
    if match:
        return _clean_label_text(match.group(1))

    prefix_match = re.search(r"\b([A-Z0-9][A-Z0-9 _-]{1,39})\s+(?:name\s*plate|nameplate|plate)\b", prompt)
    if prefix_match:
        candidate = _clean_label_text(prefix_match.group(1))
        stop_words = {"MAKE", "SMALL", "LARGE", "A", "AN", "THE"}
        parts = [part for part in candidate.split() if part.upper() not in stop_words]
        candidate = " ".join(parts).strip()
        if candidate:
            return candidate[:40]
    match = re.search(
        r"(?:name\s*plate|nameplate|plate)\s+([^,.;]+?)(?=\s+\d+(?:[.,]\d+)?\s*(?:x|by)|,|\.|$)",
        prompt,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = _clean_label_text(match.group(1))
        if candidate.lower() not in {"with", "for", "that"} and any(ch.isalpha() for ch in candidate):
            return candidate

    for candidate in re.findall(r"\b[A-Z0-9][A-Z0-9 _-]{2,39}\b", prompt):
        candidate = _clean_label_text(candidate)
        if any(ch.isalpha() for ch in candidate) and candidate.upper() not in {"MAKE", "NAME PLATE", "NAMEPLATE", "PLATE"}:
            return candidate
    return "AI LAB"


def _extract_mounting_holes(prompt: str) -> int:
    normalized = prompt.lower()
    has_hole_context = any(token in normalized for token in ["hole", "screw", "mount"])
    word_counts = {"one": 1, "two": 2, "three": 3, "four": 4}
    if has_hole_context:
        for word, count in word_counts.items():
            if word in normalized:
                return count

    match = re.search(r"(\d+)\s*(?:holes?|screw|mount)", normalized)
    if match:
        return max(0, min(4, int(match.group(1))))

    return 0


def mock_stable_json(user_prompt: str) -> str:
    lower_prompt = user_prompt.lower()
    width, height = _extract_dimensions(user_prompt)
    spec = {
        "object_type": "name_plate",
        "width_mm": width,
        "height_mm": height,
        "thickness_mm": _extract_thickness(user_prompt),
        "text": _extract_text(user_prompt),
        "text_depth_mm": 0.8,
        "raised_text": not any(token in lower_prompt for token in ["engraved", "recessed", "sunken", "cut text"]),
        "rounded_corners": not any(token in lower_prompt for token in ["sharp corners", "square corners", "no rounded"]),
        "corner_radius_mm": 2,
        "mounting_holes": _extract_mounting_holes(user_prompt),
        "hole_diameter_mm": 4,
    }
    return json.dumps(spec, ensure_ascii=True, indent=2)

def mock_experimental_code(user_prompt: str) -> str:
    text = user_prompt.lower()

    if any(word in text for word in ["vase", "vases", "vaza", "flower vase", "vessel"]):
        return """def build_model():
    import cadquery as cq
    profile = [
        (12, 0), (18, 0), (16, 12), (22, 28), (14, 45), (17, 55),
        (12, 55), (10, 45), (17, 28), (11, 12), (13, 3), (12, 3),
    ]
    model = cq.Workplane("XZ").polyline(profile).close().revolve()
    return model
"""

    if any(word in text for word in ["cup", "mug", "plant pot", "flower pot", "pot"]):
        return """def build_model():
    import cadquery as cq
    outer = cq.Workplane("XY").circle(22).extrude(45)
    inner = cq.Workplane("XY").circle(17).extrude(42).translate((0, 0, 5))
    model = outer.cut(inner)
    return model
"""

    if "bowl" in text:
        return """def build_model():
    import cadquery as cq
    outer = cq.Workplane("XY").circle(12).workplane(offset=24).circle(30).loft(combine=True)
    inner = cq.Workplane("XY").workplane(offset=4).circle(9).workplane(offset=22).circle(25).loft(combine=True)
    model = outer.cut(inner)
    return model
"""

    if any(word in text for word in ["sphere", "ball", "globe"]):
        return """def build_model():
    import cadquery as cq
    model = (
        cq.Workplane("XY")
        .circle(2)
        .workplane(offset=10).circle(18)
        .workplane(offset=14).circle(22)
        .workplane(offset=14).circle(18)
        .workplane(offset=10).circle(2)
        .loft(combine=True)
    )
    return model
"""

    if "ring" in text or "tube" in text or "donut" in text or "washer" in text:
        return """def build_model():
    import cadquery as cq
    outer = cq.Workplane("XY").circle(24).extrude(8)
    inner = cq.Workplane("XY").circle(13).extrude(10).translate((0, 0, -1))
    model = outer.cut(inner)
    return model
"""

    if "cylinder" in text:
        return """def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").circle(18).extrude(40)
    return model
"""

    if "cone" in text:
        return """def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").circle(22).workplane(offset=45).circle(3).loft(combine=True)
    return model
"""

    if "pyramid" in text:
        return """def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").rect(42, 42).workplane(offset=34).rect(1, 1).loft(combine=True)
    return model
"""

    if "rocket" in text:
        return """def build_model():
    import cadquery as cq
    body = cq.Workplane("XY").circle(10).extrude(45)
    nose = cq.Workplane("XY").workplane(offset=45).circle(10).workplane(offset=18).circle(1).loft(combine=True)
    fin1 = cq.Workplane("XY").box(4, 16, 14, centered=(True, True, False)).translate((10, 0, 0))
    fin2 = cq.Workplane("XY").box(4, 16, 14, centered=(True, True, False)).translate((-10, 0, 0))
    model = body.union(nose).union(fin1).union(fin2)
    return model
"""

    if "tree" in text:
        return """def build_model():
    import cadquery as cq
    trunk = cq.Workplane("XY").circle(5).extrude(28)
    crown = cq.Workplane("XY").workplane(offset=24).circle(24).workplane(offset=36).circle(5).loft(combine=True)
    model = trunk.union(crown)
    return model
"""

    if "car" in text:
        return """def build_model():
    import cadquery as cq
    body = cq.Workplane("XY").box(58, 28, 14, centered=(True, True, False))
    cabin = cq.Workplane("XY").box(28, 22, 14, centered=(True, True, False)).translate((2, 0, 14))
    wheel1 = cq.Workplane("YZ").circle(6).extrude(5).translate((-18, -16, 5))
    wheel2 = cq.Workplane("YZ").circle(6).extrude(5).translate((18, -16, 5))
    wheel3 = cq.Workplane("YZ").circle(6).extrude(5).translate((-18, 11, 5))
    wheel4 = cq.Workplane("YZ").circle(6).extrude(5).translate((18, 11, 5))
    model = body.union(cabin).union(wheel1).union(wheel2).union(wheel3).union(wheel4)
    return model
"""

    if "chair" in text:
        return """def build_model():
    import cadquery as cq
    seat = cq.Workplane("XY").box(34, 34, 4, centered=(True, True, False)).translate((0, 0, 22))
    back = cq.Workplane("XY").box(34, 4, 34, centered=(True, True, False)).translate((0, 15, 35))
    legs = cq.Workplane("XY").pushPoints([(-13, -13), (13, -13), (-13, 13), (13, 13)]).rect(4, 4).extrude(22)
    model = legs.union(seat).union(back)
    return model
"""

    if "table" in text:
        return """def build_model():
    import cadquery as cq
    top = cq.Workplane("XY").box(60, 38, 5, centered=(True, True, False)).translate((0, 0, 32))
    legs = cq.Workplane("XY").pushPoints([(-24, -14), (24, -14), (-24, 14), (24, 14)]).rect(5, 5).extrude(32)
    model = legs.union(top)
    return model
"""

    if "phone stand" in text or "stand" in text:
        return """def build_model():
    import cadquery as cq
    base = cq.Workplane("XY").box(70, 45, 6, centered=(True, True, False))
    back = cq.Workplane("XY").box(70, 6, 48, centered=(True, True, False)).translate((0, 16, 24))
    lip = cq.Workplane("XY").box(70, 8, 10, centered=(True, True, False)).translate((0, -16, 6))
    model = base.union(back).union(lip)
    return model
"""

    if "keychain" in text or "tag" in text:
        return """def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").box(60, 25, 3, centered=(True, True, False)).edges("|Z").fillet(4)
    model = model.faces(">Z").workplane(centerOption="CenterOfBoundBox").pushPoints([(-23, 0)]).hole(5)
    return model
"""

    if "pencil" in text or "holder" in text:
        return """def build_model():
    import cadquery as cq
    base = cq.Workplane("XY").box(70, 45, 35, centered=(True, True, False))
    points = [(-20, -10), (0, -10), (20, -10), (-20, 10), (0, 10), (20, 10)]
    model = base.faces(">Z").workplane(centerOption="CenterOfBoundBox").pushPoints(points).hole(9, depth=30)
    return model
"""

    if "open box" in text or "tray" in text or "box" in text:
        return """def build_model():
    import cadquery as cq
    outer = cq.Workplane("XY").box(60, 40, 25, centered=(True, True, False))
    inner = cq.Workplane("XY").box(56, 36, 24, centered=(True, True, False)).translate((0, 0, 2))
    model = outer.cut(inner)
    return model
"""

    if "cube" in text and "hole" in text:
        return """def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").box(30, 30, 30).faces(">Z").workplane().hole(12)
    return model
"""

    return """def build_model():
    import cadquery as cq
    model = cq.Workplane("XY").circle(18).extrude(12).faces(">Z").workplane().circle(10).extrude(10)
    return model
"""

def mock_repair_code(user_prompt: str) -> str:
    return mock_experimental_code(user_prompt)



