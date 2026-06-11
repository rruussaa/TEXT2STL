# Architecture

Text2STL Agent has two generation paths.

## Stable Path

```text
Prompt -> LLM/mock JSON -> NamePlateSpec -> CadQuery template -> STL -> trimesh report
```

The stable path is constrained to one model family: printable name plates. The LLM is only asked to extract a JSON specification. Pydantic validates dimensions, text length, hole count, and other parameters before CadQuery receives them.

This makes stable mode predictable enough for a live class demo.

## Experimental Path

```text
Prompt -> template-assisted CadQuery or LLM CadQuery code -> AST safety check -> subprocess runner -> STL -> trimesh report
```

The experimental path has two layers:

1. For common demo objects, a curated CadQuery template is used first. This improves recognizability and watertight STL quality.
2. For unknown objects, the LLM generates CadQuery code. If execution fails, the traceback is sent to the LLM repair prompt. The system retries at most two repairs.

Generated or template code must define:

```python
def build_model():
    import cadquery as cq
    ...
    return model
```

The runner executes this function in a separate Python subprocess with a 10 second timeout.

## Quality Gate

Experimental code is checked for safety and basic semantic quality. For known object requests, the app checks for recognizable features such as wings/tail for airplanes, wheels/cabin for cars, and roof/door/windows for houses. Generic primitives are rejected for non-primitive requests.

## LLM Modes

- `LLM_MODE=mock`: deterministic demo output, no API key required
- `LLM_MODE=openai_compatible`: OpenAI-compatible chat completions endpoint
- Ollama can be used through `http://host.docker.internal:11434/v1` in Docker or `http://127.0.0.1:11434/v1` locally

## Scope

The project stops at STL export. Slicing, G-code generation, and printer control are intentionally outside the scope.
