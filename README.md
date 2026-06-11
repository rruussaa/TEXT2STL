# Text2STL Agent

## Quick Start

CPU-only Docker run:

```bash
docker compose up --build
```

CPU mode uses shorter experimental LLM responses so local CPU generation is less likely to run into long Ollama timeouts:

```text
LLM_COMPACT_GENERATION=true
LLM_EXPERIMENTAL_MAX_TOKENS=600
LLM_REPAIR_MAX_TOKENS=450
LLM_TIMEOUT_SEC=180
LLM_ACCELERATOR=cpu
LLM_MAX_REPAIRS=2
```

NVIDIA GPU Docker run:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

GPU mode enables Docker GPU access for Ollama and restores the longer experimental generation settings:

```text
LLM_COMPACT_GENERATION=false
LLM_EXPERIMENTAL_MAX_TOKENS=900
LLM_REPAIR_MAX_TOKENS=900
LLM_TIMEOUT_SEC=120
LLM_ACCELERATOR=gpu
LLM_MAX_REPAIRS=4
```

GPU mode requires:

- an NVIDIA GPU with current NVIDIA drivers
- Docker Desktop or Docker Engine
- NVIDIA Container Toolkit / NVIDIA GPU support enabled for Docker

Before running the app, verify Docker can see the GPU:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

If `nvidia-smi` prints the GPU table, run:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

If Docker cannot see the GPU, use the CPU-only command instead:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8501
```

The Compose setup starts three services:

```text
ollama      local LLM server
ollama-pull downloads qwen3:8b into a persistent Docker volume
text2stl    Streamlit app
```

The first run can take a while because Docker downloads the images and Ollama pulls the 5.2 GB Qwen3 model. Later runs reuse the cached model.

It is normal for `ollama-pull` to exit with code `0` after the model is downloaded. The app should keep running as `text2stl` on `http://localhost:8501`.

If Compose reports a stale container error after `ollama-pull` succeeds, stop the attached terminal with `Ctrl+C` and restart detached:

```bash
docker compose up -d
```

For GPU mode, restart detached with the GPU override:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

To confirm Ollama is using the GPU, check the Ollama logs and look for a GPU compute backend instead of `id=cpu`:

```bash
docker compose logs ollama
```

The Streamlit header also shows runtime status. Before a model is loaded it shows the configured mode, and after generation starts it reports whether Ollama is using CPU or GPU VRAM according to Ollama's `/api/ps` status.

To stop:

```bash
docker compose down
```

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

## Run Locally With Ollama

This project is configured for a local OpenAI-compatible Ollama server using Qwen3 8B.

For most users, Docker Compose is easier because it starts both Ollama and the app. Use this manual local setup only if you want to run Ollama and Streamlit directly on Windows.

On this setup, Ollama is installed under:

```text
D:\FMI\LLM_proekt\ollama-app
```

and models are stored under:

```text
D:\FMI\LLM_proekt\ollama-models
```

Start Ollama with:

```powershell
.\scripts\start_ollama_d.ps1
```

Then make sure the model is available:

```bash
D:\FMI\LLM_proekt\ollama-app\ollama.exe pull qwen3:8b
```

Create `.env` from `.env.example`:

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen3:8b
LLM_ACCELERATOR=cpu
LLM_TIMEOUT_SEC=180
LLM_COMPACT_GENERATION=true
LLM_EXPERIMENTAL_MAX_TOKENS=600
LLM_REPAIR_MAX_TOKENS=450
LLM_MAX_REPAIRS=2
```

Install Python dependencies and run the UI:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run ui\streamlit_app.py
```

Open `http://localhost:8501`.

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
