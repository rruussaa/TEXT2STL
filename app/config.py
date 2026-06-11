"""Runtime configuration for Text2STL Agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv_if_present(path: Path | None = None) -> None:
    """Load simple KEY=VALUE pairs from .env without requiring python-dotenv."""
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    llm_mode: str = "mock"
    llm_base_url: str = "http://host.docker.internal:11434/v1"
    llm_api_key: str = "dummy"
    llm_model: str = "qwen2.5-coder:7b"
    llm_accelerator: str = "cpu"
    llm_timeout_sec: float = 180.0
    llm_experimental_max_tokens: int = 600
    llm_repair_max_tokens: int = 450
    llm_max_repairs: int = 2
    llm_compact_generation: bool = True
    output_dir: Path = PROJECT_ROOT / "outputs"


def _env_float(name: str, default: float, minimum: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        return max(minimum, float(raw_value))
    except ValueError:
        return default


def _env_int(name: str, default: int, minimum: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return max(minimum, int(raw_value))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    load_dotenv_if_present()
    output_dir = Path(os.getenv("OUTPUT_DIR", str(PROJECT_ROOT / "outputs")))
    output_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        llm_mode=os.getenv("LLM_MODE", "mock").strip().lower(),
        llm_base_url=os.getenv("LLM_BASE_URL", "http://host.docker.internal:11434/v1"),
        llm_api_key=os.getenv("LLM_API_KEY", "dummy"),
        llm_model=os.getenv("LLM_MODEL", "qwen2.5-coder:7b"),
        llm_accelerator=os.getenv("LLM_ACCELERATOR", "cpu").strip().lower(),
        llm_timeout_sec=_env_float("LLM_TIMEOUT_SEC", 180.0, 30.0),
        llm_experimental_max_tokens=_env_int("LLM_EXPERIMENTAL_MAX_TOKENS", 600, 100),
        llm_repair_max_tokens=_env_int("LLM_REPAIR_MAX_TOKENS", 450, 100),
        llm_max_repairs=_env_int("LLM_MAX_REPAIRS", 2, 0),
        llm_compact_generation=_env_bool("LLM_COMPACT_GENERATION", True),
        output_dir=output_dir,
    )


def prompt_path(name: str) -> Path:
    return PROJECT_ROOT / "prompts" / name


def read_prompt(name: str) -> str:
    return prompt_path(name).read_text(encoding="utf-8")
