"""User feedback capture for generated models."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def feedback_path(output_dir: Path) -> Path:
    return output_dir / "feedback" / "feedback.jsonl"


def save_generation_feedback(
    result: dict[str, Any],
    rating: int,
    notes: str,
    accepted_for_training: bool,
    output_dir: Path,
) -> dict[str, Any]:
    path = feedback_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "id": uuid4().hex,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "mode": result.get("mode"),
        "prompt": result.get("prompt", ""),
        "rating": int(rating),
        "notes": notes.strip(),
        "accepted_for_training": bool(accepted_for_training),
        "success": bool(result.get("success")),
        "validation_pass": bool(result.get("validation_pass")),
        "validation": result.get("validation", {}),
        "code": result.get("code", ""),
        "spec": result.get("spec"),
        "output_path": result.get("output_path"),
        "attempts": result.get("attempts", []),
        "error": result.get("error", ""),
    }

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")
    return record
