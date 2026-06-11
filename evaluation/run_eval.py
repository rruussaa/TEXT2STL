"""Run a small evaluation set through the Text2STL pipelines."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from app.pipeline import run_experimental_pipeline, run_stable_pipeline


FIELDS = [
    "id",
    "mode",
    "json_valid",
    "code_safe",
    "stl_generated",
    "validation_pass",
    "repair_attempts",
    "time_sec",
    "warnings",
    "error",
]


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _row_from_result(item: dict, result: dict, elapsed: float) -> dict:
    warnings = result.get("validation", {}).get("warnings", [])
    return {
        "id": item["id"],
        "mode": item["mode"],
        "json_valid": result.get("json_valid", ""),
        "code_safe": result.get("code_safe", ""),
        "stl_generated": result.get("stl_generated", False),
        "validation_pass": result.get("validation_pass", False),
        "repair_attempts": result.get("repair_attempts", 0),
        "time_sec": round(elapsed, 3),
        "warnings": len(warnings),
        "error": (result.get("error") or "")[:500],
    }


def run_eval(input_path: Path, output_path: Path) -> list[dict]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for item in _load_jsonl(input_path):
        start = time.perf_counter()
        if item["mode"] == "stable":
            result = run_stable_pipeline(item["prompt"])
        else:
            result = run_experimental_pipeline(item["prompt"])
        elapsed = time.perf_counter() - start
        results.append(_row_from_result(item, result, elapsed))

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Text2STL Agent prompts.")
    parser.add_argument("--input", default="evaluation/test_prompts.jsonl")
    parser.add_argument("--out", default="evaluation/results.csv")
    args = parser.parse_args()

    rows = run_eval(Path(args.input), Path(args.out))
    print(f"Wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

