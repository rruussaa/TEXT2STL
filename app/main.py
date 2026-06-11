"""Command line interface for Text2STL Agent."""

from __future__ import annotations

import argparse
import json
import sys

from app.pipeline import run_experimental_pipeline, run_stable_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate STL files from text prompts.")
    parser.add_argument("--mode", choices=["stable", "experimental"], required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", default=None, help="Optional STL output path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.mode == "stable":
        result = run_stable_pipeline(args.prompt, output_path=args.output)
    else:
        result = run_experimental_pipeline(args.prompt, output_path=args.output)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("stl_generated") else 1


if __name__ == "__main__":
    sys.exit(main())

