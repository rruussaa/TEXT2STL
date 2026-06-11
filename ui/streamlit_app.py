"""Streamlit UI for Text2STL Agent."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import re
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.config import get_settings
from app.feedback import save_generation_feedback
from app.pipeline import run_experimental_pipeline, run_stable_pipeline
from app.stl_preview import build_stl_preview_figure


STABLE_EXAMPLES = [
    "Make a 100 by 35 mm name plate with text AI LAB, 3 mm thick, with two screw holes.",
    "Make a small TEXT2STL name plate 80 by 25 mm with rounded corners.",
]
HEADER_IMAGE_CANDIDATES = (
    PROJECT_ROOT / "ui" / "assets" / "model-woman.jpg",
    PROJECT_ROOT / "ui" / "assets" / "model-woman.jpeg",
    PROJECT_ROOT / "ui" / "assets" / "model-woman.png",
)

EXPERIMENTAL_EXAMPLES = [
    "Make a small hollow vase with a narrow neck.",
    "Make a 30 mm cube with a cylindrical hole through the center.",
    "Make a simple pencil holder with six circular holes.",
    "Make a small open box 60 by 40 by 25 mm with 2 mm walls.",
]


def _ollama_api_base(llm_base_url: str) -> str | None:
    base_url = llm_base_url.rstrip("/")
    if base_url.endswith("/v1"):
        return base_url[:-3]
    if "11434" in base_url:
        return base_url
    return None


def _format_bytes(value: int) -> str:
    if value <= 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


@st.cache_data(ttl=5, show_spinner=False)
def _ollama_runtime_status(llm_base_url: str, configured_accelerator: str) -> str:
    configured = configured_accelerator.upper() if configured_accelerator else "UNKNOWN"
    api_base = _ollama_api_base(llm_base_url)
    if not api_base:
        return f"configured {configured}"

    try:
        with urlopen(f"{api_base}/api/ps", timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return f"configured {configured}; Ollama status unavailable"

    models = payload.get("models") or []
    if not models:
        return f"configured {configured}; no model loaded yet"

    vram_bytes = sum(int(model.get("size_vram") or 0) for model in models)
    active = "GPU active" if vram_bytes > 0 else "CPU active"
    return f"{active}; configured {configured}; VRAM {_format_bytes(vram_bytes)}"


def _set_prompt(prompt: str) -> None:
    st.session_state["prompt"] = prompt


def _feedback_key(result: dict) -> str:
    value = str(result.get("output_path") or result.get("prompt") or "latest")
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value)[-80:]


def _show_feedback_form(result: dict, output_dir: Path) -> None:
    st.subheader("User rating")
    default_training = bool(result.get("success") and result.get("validation_pass"))
    with st.form(f"feedback_{_feedback_key(result)}"):
        rating = st.slider("Rating", min_value=1, max_value=5, value=4 if default_training else 3)
        notes = st.text_area("Feedback", placeholder="What should be better about this STL?")
        accepted = st.checkbox("Use as training example", value=default_training)
        submitted = st.form_submit_button("Save rating", use_container_width=True)

    if submitted:
        record = save_generation_feedback(
            result=result,
            rating=rating,
            notes=notes,
            accepted_for_training=accepted,
            output_dir=output_dir,
        )
        st.success(f"Saved rating {record['id']}")


def _show_download(path_value: str | None) -> None:
    if not path_value:
        return
    path = Path(path_value)
    if not path.exists():
        return
    with path.open("rb") as handle:
        st.download_button(
            "Download STL",
            data=handle,
            file_name=path.name,
            mime="model/stl",
            use_container_width=True,
        )


def _show_preview(path_value: str | None) -> None:
    if not path_value:
        st.info("Generate an STL file to see a preview.")
        return

    path = Path(path_value)
    if not path.exists():
        st.info("No STL file is available for preview.")
        return

    try:
        figure = build_stl_preview_figure(str(path))
        st.plotly_chart(
            figure,
            use_container_width=True,
            config={"displaylogo": False, "scrollZoom": True},
        )
    except Exception as exc:
        st.warning(f"Preview could not be rendered: {exc}")


def _header_image_path() -> Path | None:
    for path in HEADER_IMAGE_CANDIDATES:
        if path.exists():
            return path
    return None


def _hide_streamlit_deploy_button() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stDeployButton"] {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )



def _panda_loader_html() -> str:
    return """
    <style>
        .panda-loader {
            width: 100%;
            border: 1px solid rgba(37, 99, 42, 0.22);
            border-radius: 8px;
            padding: 14px 16px;
            margin: 8px 0 16px 0;
            background: linear-gradient(90deg, #f7f3dc 0%, #f0f7ea 52%, #fff7e1 100%);
            box-shadow: 0 10px 26px rgba(21, 58, 35, 0.10);
            overflow: hidden;
        }
        .panda-loader-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
        }
        .panda-loader-copy {
            min-width: 170px;
            color: #1f3323;
            font-family: sans-serif;
        }
        .panda-loader-copy strong {
            display: block;
            font-size: 1.02rem;
            font-weight: 700;
            margin-bottom: 2px;
        }
        .panda-loader-copy span {
            display: inline-block;
            font-size: 0.86rem;
            color: #47634b;
        }
        .panda-loader-copy span::after {
            content: "";
            animation: panda-dots 1.2s steps(4, end) infinite;
        }
        .panda-track {
            display: grid;
            grid-template-columns: repeat(4, minmax(74px, 1fr));
            gap: 10px;
            width: 100%;
        }
        .panda-pose {
            position: relative;
            height: 96px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.66);
            border: 1px solid rgba(31, 51, 35, 0.12);
            overflow: hidden;
        }
        .panda-pose::before {
            content: "";
            position: absolute;
            left: 10px;
            right: 10px;
            bottom: 13px;
            height: 4px;
            border-radius: 999px;
            background: rgba(31, 51, 35, 0.14);
        }
        .panda-pose svg {
            position: absolute;
            inset: 4px 0 0 0;
            width: 100%;
            height: 88px;
            transform-origin: 50% 74%;
        }
        .panda-pose:nth-child(1) svg { animation: panda-bow 1.18s ease-in-out infinite; }
        .panda-pose:nth-child(2) svg { animation: panda-kick 1.05s ease-in-out infinite; animation-delay: 0.10s; }
        .panda-pose:nth-child(3) svg { animation: panda-punch 1.10s ease-in-out infinite; animation-delay: 0.18s; }
        .panda-pose:nth-child(4) svg { animation: panda-hop 1.22s ease-in-out infinite; animation-delay: 0.28s; }
        .bamboo {
            stroke: #6d8f38;
            stroke-width: 3;
            stroke-linecap: round;
            opacity: 0.45;
        }
        .panda-white { fill: #fffdf4; stroke: #151515; stroke-width: 2; }
        .panda-black { fill: #151515; stroke: #151515; stroke-width: 2; }
        .panda-accent { fill: #d1462f; stroke: #151515; stroke-width: 1.6; }
        .panda-limb { stroke: #151515; stroke-width: 11; stroke-linecap: round; fill: none; }
        .panda-limb-thin { stroke: #151515; stroke-width: 8; stroke-linecap: round; fill: none; }
        .panda-eye { fill: #fffdf4; }
        @keyframes panda-dots {
            0% { content: ""; }
            25% { content: "."; }
            50% { content: ".."; }
            75%, 100% { content: "..."; }
        }
        @keyframes panda-bow {
            0%, 100% { transform: translateY(0) rotate(-2deg); }
            50% { transform: translateY(4px) rotate(4deg); }
        }
        @keyframes panda-kick {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            45% { transform: translateY(-3px) rotate(-5deg); }
        }
        @keyframes panda-punch {
            0%, 100% { transform: translateX(0); }
            50% { transform: translateX(5px); }
        }
        @keyframes panda-hop {
            0%, 100% { transform: translateY(0) scale(1); }
            50% { transform: translateY(-7px) scale(1.03); }
        }
        @media (max-width: 720px) {
            .panda-loader-row { flex-direction: column; align-items: stretch; }
            .panda-track { grid-template-columns: repeat(2, minmax(100px, 1fr)); }
        }
    </style>
    <div class="panda-loader" role="status" aria-live="polite">
        <div class="panda-loader-row">
            <div class="panda-loader-copy">
                <strong>Generating STL</strong>
                <span>Training the model</span>
            </div>
            <div class="panda-track">
                <div class="panda-pose">
                    <svg viewBox="0 0 120 120" aria-hidden="true">
                        <path class="bamboo" d="M18 84 L18 18 M13 45 L23 39 M13 64 L24 58" />
                        <path class="panda-limb" d="M47 74 Q35 84 25 75" />
                        <path class="panda-limb" d="M73 74 Q85 84 96 74" />
                        <path class="panda-limb" d="M50 92 Q41 104 31 103" />
                        <path class="panda-limb" d="M70 92 Q79 104 90 103" />
                        <ellipse class="panda-white" cx="60" cy="75" rx="24" ry="28" />
                        <circle class="panda-black" cx="43" cy="42" r="10" />
                        <circle class="panda-black" cx="77" cy="42" r="10" />
                        <circle class="panda-white" cx="60" cy="50" r="24" />
                        <ellipse class="panda-black" cx="51" cy="50" rx="7" ry="9" transform="rotate(-22 51 50)" />
                        <ellipse class="panda-black" cx="69" cy="50" rx="7" ry="9" transform="rotate(22 69 50)" />
                        <circle class="panda-eye" cx="52" cy="49" r="2" />
                        <circle class="panda-eye" cx="68" cy="49" r="2" />
                        <path class="panda-black" d="M57 59 Q60 62 63 59 Q60 67 57 59" />
                        <path class="panda-accent" d="M47 70 Q60 78 73 70 L70 80 Q60 86 50 80 Z" />
                    </svg>
                </div>
                <div class="panda-pose">
                    <svg viewBox="0 0 120 120" aria-hidden="true">
                        <path class="bamboo" d="M101 86 L101 16 M96 38 L106 32 M95 62 L107 55" />
                        <path class="panda-limb" d="M47 72 Q31 66 24 52" />
                        <path class="panda-limb" d="M74 71 Q91 67 101 55" />
                        <path class="panda-limb" d="M53 92 Q43 104 34 103" />
                        <path class="panda-limb" d="M70 89 Q88 72 102 66" />
                        <ellipse class="panda-white" cx="61" cy="74" rx="23" ry="28" />
                        <circle class="panda-black" cx="44" cy="41" r="10" />
                        <circle class="panda-black" cx="78" cy="41" r="10" />
                        <circle class="panda-white" cx="61" cy="49" r="24" />
                        <ellipse class="panda-black" cx="52" cy="49" rx="7" ry="9" transform="rotate(-18 52 49)" />
                        <ellipse class="panda-black" cx="70" cy="49" rx="7" ry="9" transform="rotate(18 70 49)" />
                        <circle class="panda-eye" cx="53" cy="48" r="2" />
                        <circle class="panda-eye" cx="69" cy="48" r="2" />
                        <path class="panda-black" d="M58 58 Q61 61 64 58 Q61 66 58 58" />
                        <path class="panda-accent" d="M47 70 Q61 78 75 70 L71 80 Q61 85 51 80 Z" />
                    </svg>
                </div>
                <div class="panda-pose">
                    <svg viewBox="0 0 120 120" aria-hidden="true">
                        <path class="bamboo" d="M16 87 L16 20 M11 42 L22 35 M10 66 L23 59" />
                        <path class="panda-limb" d="M46 72 Q29 76 22 89" />
                        <path class="panda-limb" d="M74 71 Q91 63 103 64" />
                        <path class="panda-limb" d="M51 91 Q44 104 33 105" />
                        <path class="panda-limb" d="M70 91 Q82 100 94 95" />
                        <ellipse class="panda-white" cx="61" cy="75" rx="24" ry="28" />
                        <circle class="panda-black" cx="44" cy="41" r="10" />
                        <circle class="panda-black" cx="78" cy="41" r="10" />
                        <circle class="panda-white" cx="61" cy="50" r="24" />
                        <ellipse class="panda-black" cx="52" cy="50" rx="7" ry="9" transform="rotate(-18 52 50)" />
                        <ellipse class="panda-black" cx="70" cy="50" rx="7" ry="9" transform="rotate(18 70 50)" />
                        <circle class="panda-eye" cx="53" cy="49" r="2" />
                        <circle class="panda-eye" cx="69" cy="49" r="2" />
                        <path class="panda-black" d="M58 59 Q61 62 64 59 Q61 67 58 59" />
                        <path class="panda-accent" d="M48 70 Q61 77 74 70 L71 80 Q61 85 51 80 Z" />
                    </svg>
                </div>
                <div class="panda-pose">
                    <svg viewBox="0 0 120 120" aria-hidden="true">
                        <path class="bamboo" d="M101 86 L101 17 M96 37 L107 31 M95 62 L108 56" />
                        <path class="panda-limb-thin" d="M45 70 Q34 58 28 43" />
                        <path class="panda-limb-thin" d="M75 70 Q87 57 93 42" />
                        <path class="panda-limb" d="M51 92 Q43 103 33 101" />
                        <path class="panda-limb" d="M69 92 Q79 103 91 101" />
                        <ellipse class="panda-white" cx="60" cy="74" rx="23" ry="29" />
                        <circle class="panda-black" cx="43" cy="39" r="10" />
                        <circle class="panda-black" cx="77" cy="39" r="10" />
                        <circle class="panda-white" cx="60" cy="48" r="24" />
                        <ellipse class="panda-black" cx="51" cy="48" rx="7" ry="9" transform="rotate(-20 51 48)" />
                        <ellipse class="panda-black" cx="69" cy="48" rx="7" ry="9" transform="rotate(20 69 48)" />
                        <circle class="panda-eye" cx="52" cy="47" r="2" />
                        <circle class="panda-eye" cx="68" cy="47" r="2" />
                        <path class="panda-black" d="M57 58 Q60 61 63 58 Q60 66 57 58" />
                        <path class="panda-accent" d="M47 69 Q60 77 73 69 L70 79 Q60 85 50 79 Z" />
                    </svg>
                </div>
            </div>
        </div>
    </div>
    """

def main() -> None:
    st.set_page_config(page_title="TEXT2STL Model", layout="wide")
    _hide_streamlit_deploy_button()
    settings = get_settings()
    header_image_path = _header_image_path()
    header_text, header_photo = st.columns([5, 1])
    with header_text:
        st.title("TEXT2STL Model")
        st.caption(f"LLM mode: {settings.llm_mode} | model: {settings.llm_model}")
        st.caption(f"Runtime: {_ollama_runtime_status(settings.llm_base_url, settings.llm_accelerator)}")
    with header_photo:
        if header_image_path:
            st.image(str(header_image_path), width=130)
    loader_slot = st.empty()
    if "prompt" not in st.session_state:
        st.session_state["prompt"] = STABLE_EXAMPLES[0]

    mode_label = st.radio(
        "Mode",
        ["Stable name plate", "Experimental free-form"],
        horizontal=True,
    )
    mode = "stable" if mode_label == "Stable name plate" else "experimental"
    if mode == "experimental" and settings.llm_mode == "mock":
        st.warning("Experimental mode is using mock code generation. Set LLM_MODE=openai_compatible for real local or API generation.")

    with st.expander("Example prompts", expanded=True):
        examples = STABLE_EXAMPLES if mode == "stable" else EXPERIMENTAL_EXAMPLES
        columns = st.columns(len(examples))
        for column, example in zip(columns, examples):
            with column:
                st.button(
                    example,
                    key=f"example_{mode}_{example}",
                    on_click=_set_prompt,
                    args=(example,),
                    use_container_width=True,
                )

    prompt = st.text_area("Prompt", key="prompt", height=120)
    generate = st.button("Generate STL", type="primary", use_container_width=True)

    if generate:
        loader_slot.markdown(_panda_loader_html(), unsafe_allow_html=True)
        try:
            with st.spinner("Generating STL..."):
                if mode == "stable":
                    result = run_stable_pipeline(prompt)
                else:
                    result = run_experimental_pipeline(prompt)
                st.session_state["last_result"] = result
        finally:
            loader_slot.empty()

    result = st.session_state.get("last_result")
    if not result:
        return

    st.subheader("Prompt")
    st.write(result.get("prompt", ""))

    left, right = st.columns([1, 1])
    with left:
        if result.get("mode") == "stable":
            st.subheader("Generated JSON")
            if result.get("spec"):
                st.json(result["spec"])
            else:
                st.code(result.get("raw_json", ""), language="json")
        else:
            st.subheader("Generated CadQuery code")
            if result.get("template_fallback"):
                st.info(f"Template-assisted generation used: {result.get('template_name', 'known object')}")
            if result.get("quality_issues"):
                st.warning("Quality notes: " + "; ".join(result.get("quality_issues", [])))
            st.code(result.get("code", ""), language="python")

    with right:
        st.subheader("Model preview")
        if result.get("local_fallback"):
            st.info("Local demo fallback: CadQuery is not installed, so a simple STL preview was generated without executing CadQuery.")
        _show_preview(result.get("output_path"))

    report, download = st.columns([1, 1])
    with report:
        st.subheader("STL validation report")
        if result.get("validation"):
            st.json(result["validation"])
        else:
            st.info("No validation report was produced.")

    with download:
        st.subheader("STL file")
        _show_download(result.get("output_path"))

    _show_feedback_form(result, settings.output_dir)

    if result.get("attempts"):
        st.subheader("Repair attempts")
        for attempt in result["attempts"]:
            suffix = "template" if attempt.get("template") else ("repair" if attempt.get("repair") else "llm")
            label = f"Attempt {attempt['attempt']} ({suffix}) - {'success' if attempt['success'] else 'failed'}"
            with st.expander(label, expanded=not attempt["success"]):
                st.write(
                    {
                        "code_safe": attempt.get("code_safe"),
                        "safety_errors": attempt.get("safety_errors", []),
                        "quality_ok": attempt.get("quality_ok"),
                        "quality_issues": attempt.get("quality_issues", []),
                        "validation_pass": attempt.get("validation_pass"),
                        "validation_warnings": attempt.get("validation", {}).get("warnings", []),
                    }
                )
                st.code(attempt.get("code", ""), language="python")
                if attempt.get("traceback"):
                    st.code(attempt["traceback"], language="text")

    if result.get("error"):
        st.error(result["error"])


if __name__ == "__main__":
    main()





