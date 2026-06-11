"""Prepare supervised fine-tuning data from feedback or curated examples.

Input JSONL records can come from:
- UI feedback records written to outputs/feedback/feedback.jsonl
- a curated dataset with at least {"prompt": "...", "code": "..."}

The output is JSONL with chat-style records:
{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}], "metadata": ...}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYSTEM_PROMPT = (PROJECT_ROOT / "prompts" / "experimental_cadquery_prompt.md").read_text(encoding="utf-8")


def _iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number}: expected JSON object")
            yield payload


def _accepted_feedback(record: dict, min_rating: int) -> bool:
    return bool(
        record.get("accepted_for_training")
        and int(record.get("rating") or 0) >= min_rating
        and record.get("validation_pass")
        and record.get("prompt")
        and record.get("code")
    )


def _accepted_curated(record: dict, min_rating: int) -> bool:
    if record.get("rating") is not None and int(record.get("rating") or 0) < min_rating:
        return False
    if record.get("validation_pass") is False:
        return False
    return bool(record.get("prompt") and record.get("code"))


def _to_sft_record(record: dict, source: str, system_prompt: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": str(record["prompt"]).strip()},
            {"role": "assistant", "content": str(record["code"]).strip()},
        ],
        "metadata": {
            "source": source,
            "source_id": record.get("id"),
            "rating": record.get("rating"),
            "validation_pass": record.get("validation_pass"),
            "output_path": record.get("output_path"),
        },
    }


def prepare_dataset(
    feedback_paths: list[Path],
    dataset_paths: list[Path],
    output_path: Path,
    min_rating: int,
    system_prompt: str,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    seen: set[tuple[str, str]] = set()

    with output_path.open("w", encoding="utf-8") as output:
        for path in feedback_paths:
            for record in _iter_jsonl(path):
                if not _accepted_feedback(record, min_rating):
                    continue
                key = (str(record["prompt"]).strip(), str(record["code"]).strip())
                if key in seen:
                    continue
                seen.add(key)
                output.write(json.dumps(_to_sft_record(record, "feedback", system_prompt), ensure_ascii=True) + "\n")
                count += 1

        for path in dataset_paths:
            for record in _iter_jsonl(path):
                if not _accepted_curated(record, min_rating):
                    continue
                key = (str(record["prompt"]).strip(), str(record["code"]).strip())
                if key in seen:
                    continue
                seen.add(key)
                output.write(json.dumps(_to_sft_record(record, "curated", system_prompt), ensure_ascii=True) + "\n")
                count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Text2STL supervised fine-tuning data.")
    parser.add_argument("--feedback", action="append", type=Path, default=[], help="Feedback JSONL path.")
    parser.add_argument("--dataset", action="append", type=Path, default=[], help="Curated dataset JSONL path.")
    parser.add_argument("--out", type=Path, required=True, help="Output SFT JSONL path.")
    parser.add_argument("--min-rating", type=int, default=4, help="Minimum rating for accepted records.")
    args = parser.parse_args()

    if not args.feedback and not args.dataset:
        parser.error("Provide at least one --feedback or --dataset path.")

    count = prepare_dataset(
        feedback_paths=args.feedback,
        dataset_paths=args.dataset,
        output_path=args.out,
        min_rating=args.min_rating,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
    )
    print(f"Wrote {count} SFT records to {args.out}")


if __name__ == "__main__":
    main()
