# Text2STL Agent

## Quick Start

```bash
docker compose up --build
```

Open:

```text
http://localhost:8501
```

Default mode is `mock`, so the project can run without an API key.

## What It Does

Text2STL Agent converts natural language prompts into STL files for human review and manual slicing.

The Streamlit UI includes an interactive STL preview window, so generated models can be rotated and zoomed in the browser before downloading.

The project deliberately stops at:

```text
Text -> STL -> human review -> manual slicing -> manual printing
```

It does not generate G-code, run a slicer, or control a printer.

## Modes

Stable mode:

```text
User prompt -> JSON specification -> CadQuery name plate template -> STL -> validation report
```

Stable mode is reliable for name plates. The LLM only extracts JSON; Pydantic validates the values before CadQuery runs.

Experimental mode:

```text
User prompt -> template-assisted generation or LLM-generated CadQuery -> AST safety check -> subprocess timeout -> STL -> validation report
```

For common demo objects such as airplane, car, vase, house, chair, table, rocket, robot, tree, bowl, mug, bridge, stairs, pencil holder, phone stand, and open box, the app uses curated CadQuery templates first. This produces more recognizable, watertight STL files for live demos.

For unknown objects, the app still asks the LLM to generate CadQuery code. That code is checked with AST safety rules, executed in a subprocess with timeout, and repaired up to two times if execution fails.

## Example Prompts

Stable:

```text
Make a 100 by 35 mm name plate with text AI LAB, 3 mm thick, with two screw holes.
```

```text
Make a small TEXT2STL name plate 80 by 25 mm with rounded corners.
```

Experimental:

```text
Make a simple airplane with wings and a tail.
```

```text
Make a toy car with four wheels and a cabin.
```

```text
Make a small hollow vase with a narrow neck.
```

```text
Make a simple pencil holder with six circular holes.
```

## Run With Ollama

Start Ollama on the host and pull a coding model:

```bash
ollama pull qwen2.5-coder:7b
```

Create `.env`:

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen2.5-coder:7b
```

For local Windows runs outside Docker, use:

```env
LLM_BASE_URL=http://127.0.0.1:11434/v1
```

Then run:

```bash
docker compose up --build
```

## Run With OpenAI-Compatible API

Create `.env`:

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_key_here
LLM_MODEL=your_model_here
```

Then run:

```bash
docker compose up --build
```

## CLI

From inside the container, or from a local environment with the dependencies installed:

```bash
python -m app.main --mode stable --prompt "Make a 100 by 35 mm name plate with text AI LAB"
```

```bash
python -m app.main --mode experimental --prompt "Make a toy car with four wheels and a cabin"
```

## Local Demo Without Docker

Docker/conda is still the recommended path because CadQuery has heavy CAD dependencies. For a quick UI demo on a machine without Docker, install the lightweight dependencies and run Streamlit locally:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-local.txt
.venv\Scripts\python -m streamlit run ui/streamlit_app.py
```

In this local fallback path, stable mode can export a simple STL preview without CadQuery. The full CadQuery name plate generator, mounting holes, and experimental CadQuery execution are intended for the Docker/conda setup.

## Evaluation

```bash
python -m evaluation.run_eval --input evaluation/test_prompts.jsonl --out evaluation/results.csv
```

The CSV columns are:

```text
id,mode,json_valid,code_safe,stl_generated,validation_pass,repair_attempts,time_sec,warnings,error
```

## STL Validation

Each generated STL is checked with `trimesh` for:

- file existence and file size
- triangle count
- bounding box dimensions
- volume
- watertightness
- printer bounds fit
- warnings for empty, too small, too large, non-watertight, or invalid-volume meshes

Generated files are written to `outputs/`.

## Safety Note

Experimental generated code is executed inside the application container with AST checks and timeout. This is a research prototype and not a production-grade sandbox.

The AST checker blocks unsafe imports and calls such as `os`, `sys`, `subprocess`, `pathlib`, `socket`, `requests`, `shutil`, `builtins`, `open()`, `eval()`, `exec()`, `compile()`, `__import__()`, dunder attributes, and unreliable CadQuery calls such as `.mirror()`. Only `cadquery` and `math` imports are allowed.

## Project Structure

```text
text2stl-agent/
  app/             core config, LLM client, pipelines, schemas, validation, safety
  generators/      stable CadQuery templates
  experimental/    generated-code runner, repair loop, quality checks, object templates
  prompts/         LLM prompts
  ui/              Streamlit app
  evaluation/      JSONL test prompts and CSV evaluation script
  outputs/         generated STL files
  docs/            architecture, demo script, limitations
```
