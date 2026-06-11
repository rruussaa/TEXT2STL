"""Download and normalize the Text-to-CadQuery dataset.

Source:
https://huggingface.co/ricemonster/NeurIPS11092/tree/main/data

The downloaded JSONL files are kept outside the repo by default:
D:/FMI/LLM_proekt/datasets/text-to-cadquery

The normalized output is scaled from meters to millimeters by default and
written as a curated JSONL file with:
{"prompt": "...", "code": "...", "source": "text-to-cadquery", ...}
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen


DATASET_BASE_URL = "https://huggingface.co/ricemonster/NeurIPS11092/resolve/main/data"
DATASET_FILES = {
    "train": "data_train.jsonl",
    "val": "data_val.jsonl",
    "test": "data_test.jsonl",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_KEYS = ("prompt", "instruction", "input", "question", "description", "text")
CODE_KEYS = ("code", "cadquery", "completion", "output", "response", "answer")
FENCE_RE = re.compile(r"```(?:python|py|cadquery)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
PREFERRED_RESULT_NAMES = ("model", "assembly", "solid", "result", "part")


def default_data_dir() -> Path:
    env_path = os.environ.get("TEXT2STL_DATASET_DIR")
    if env_path:
        return Path(env_path)
    if os.name == "nt":
        return Path("D:/FMI/LLM_proekt/datasets/text-to-cadquery")
    return PROJECT_ROOT.parent / "datasets" / "text-to-cadquery"


def download_file(url: str, destination: Path, overwrite: bool) -> None:
    if destination.exists() and not overwrite:
        print(f"Using existing {destination}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "text2stl-agent-dataset-prep/1.0"})

    print(f"Downloading {url}")
    with urlopen(request) as response, destination.open("wb") as handle:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            downloaded += len(chunk)
            if total:
                print(f"\r  {downloaded / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MB", end="")
        if total:
            print()
    print(f"Saved {destination}")


def iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            yield record


def first_string(record: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def from_messages(record: dict) -> tuple[str | None, str | None]:
    messages = record.get("messages")
    if not isinstance(messages, list):
        return None, None

    prompt = None
    code = None
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "").lower()
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if role == "user":
            prompt = content.strip()
        elif role == "assistant":
            code = content.strip()
    return prompt, code


def strip_code_fences(text: str) -> str:
    text = text.strip()
    matches = FENCE_RE.findall(text)
    if not matches:
        return text

    for match in matches:
        if "import cadquery" in match or "cq." in match or "def build_model" in match:
            return match.strip()
    return matches[0].strip()


def is_export_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "export":
        return False

    value = func.value
    if isinstance(value, ast.Name) and value.id == "exporters":
        return True
    if isinstance(value, ast.Attribute) and value.attr == "exporters":
        return True
    return False


def export_target_name(node: ast.AST) -> str | None:
    if not is_export_call(node):
        return None
    call = node
    assert isinstance(call, ast.Call)
    if not call.args:
        return None
    first_arg = call.args[0]
    if isinstance(first_arg, ast.Name):
        return first_arg.id
    return None


def assigned_names(node: ast.AST) -> list[str]:
    names: list[str] = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    elif isinstance(node, ast.AugAssign):
        targets = [node.target]
    else:
        return names

    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
    return names


def indent_block(code: str, spaces: int = 4) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in code.splitlines())


def format_scale_factor(scale_factor: float) -> str:
    return f"{scale_factor:g}"


def wrap_as_build_model(code: str, scale_factor: float) -> str | None:
    if "def build_model" in code:
        return code.strip()

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    kept_nodes: list[ast.stmt] = []
    assigned: list[str] = []
    export_name: str | None = None

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and is_export_call(node.value):
            export_name = export_target_name(node.value) or export_name
            continue
        kept_nodes.append(node)
        assigned.extend(assigned_names(node))

    if not kept_nodes:
        return None

    result_name = export_name
    if not result_name:
        for preferred in PREFERRED_RESULT_NAMES:
            if preferred in assigned:
                result_name = preferred
                break
    if not result_name and assigned:
        result_name = assigned[-1]
    if not result_name:
        return None

    body = "\n".join(ast.unparse(node) for node in kept_nodes)
    if scale_factor == 1:
        model_assignment = "" if result_name == "model" else f"\nmodel = {result_name}"
    else:
        model_assignment = f"\nmodel = {result_name}.val().scale({format_scale_factor(scale_factor)})"
    wrapped = (
        "def build_model():\n"
        "    import cadquery as cq\n"
        "    import math\n"
        f"{indent_block(body)}"
        f"{indent_block(model_assignment)}\n"
        "    return model"
    )
    return wrapped.strip()


def normalize_record(record: dict, source_file: str, index: int, scale_factor: float) -> dict | None:
    prompt, code = from_messages(record)
    prompt = prompt or first_string(record, PROMPT_KEYS)
    code = code or first_string(record, CODE_KEYS)

    if not prompt or not code:
        return None

    code = strip_code_fences(code)
    if "cadquery" not in code.lower() and "cq." not in code:
        return None
    code = wrap_as_build_model(code, scale_factor)
    if not code:
        return None

    return {
        "id": record.get("id") or record.get("deepcad_id") or f"{source_file}:{index}",
        "prompt": prompt.strip(),
        "code": code.strip(),
        "source": "text-to-cadquery",
        "source_file": source_file,
    }


def normalize_files(input_paths: list[Path], output_path: Path, limit_per_file: int | None, scale_factor: float) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    seen: set[tuple[str, str]] = set()

    with output_path.open("w", encoding="utf-8") as output:
        for input_path in input_paths:
            file_written = 0
            for index, record in enumerate(iter_jsonl(input_path), start=1):
                normalized = normalize_record(record, input_path.name, index, scale_factor)
                if normalized is None:
                    skipped += 1
                    continue

                key = (normalized["prompt"], normalized["code"])
                if key in seen:
                    skipped += 1
                    continue

                seen.add(key)
                output.write(json.dumps(normalized, ensure_ascii=True) + "\n")
                written += 1
                file_written += 1

                if limit_per_file is not None and file_written >= limit_per_file:
                    break

    print(f"Wrote {written} normalized records to {output_path}")
    if skipped:
        print(f"Skipped {skipped} incomplete, duplicate, or non-CadQuery records")
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the Text-to-CadQuery dataset for Text2STL fine-tuning.")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir(), help="Directory for raw dataset files.")
    parser.add_argument(
        "--split",
        action="append",
        choices=sorted(DATASET_FILES),
        help="Dataset split to download/normalize. Repeatable. Defaults to train, val, and test.",
    )
    parser.add_argument("--skip-download", action="store_true", help="Use existing raw files only.")
    parser.add_argument("--overwrite", action="store_true", help="Re-download files that already exist.")
    parser.add_argument("--download-only", action="store_true", help="Only download raw files; do not normalize.")
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "training" / "out" / "text_to_cadquery_curated.jsonl",
        help="Normalized curated JSONL output path.",
    )
    parser.add_argument(
        "--limit-per-file",
        type=int,
        default=None,
        help="Optional small sample limit per split for quick experiments.",
    )
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=1000.0,
        help="Scale generated geometry before returning it. Default converts source meters to millimeters.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    splits = args.split or list(DATASET_FILES)
    raw_dir = args.data_dir / "raw"

    input_paths = []
    for split in splits:
        filename = DATASET_FILES[split]
        path = raw_dir / filename
        if not args.skip_download:
            download_file(f"{DATASET_BASE_URL}/{filename}", path, overwrite=args.overwrite)
        input_paths.append(path)

    if args.download_only:
        return

    missing = [path for path in input_paths if not path.exists()]
    if missing:
        missing_text = "\n".join(str(path) for path in missing)
        raise SystemExit(f"Missing dataset files. Download them first or remove --skip-download:\n{missing_text}")

    normalize_files(input_paths, args.out, args.limit_per_file, args.scale_factor)


if __name__ == "__main__":
    main()
