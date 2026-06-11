$ErrorActionPreference = "Stop"

$env:OLLAMA_MODELS = "D:\FMI\LLM_proekt\ollama-models"
New-Item -ItemType Directory -Force -Path $env:OLLAMA_MODELS | Out-Null

$ollamaPath = "D:\FMI\LLM_proekt\ollama-app\ollama.exe"

if (-not (Test-Path $ollamaPath)) {
    throw "Ollama executable was not found at $ollamaPath."
}

& $ollamaPath serve
