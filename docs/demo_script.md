# Demo Script

1. Start the app:

```bash
docker compose up --build
```

2. Open:

```text
http://localhost:8501
```

3. Keep stable mode and run:

```text
Make a 100 by 35 mm name plate with text AI LAB, 3 mm thick, with two screw holes.
```

4. Show the generated JSON, model preview window, STL validation report, and download button.

5. Rotate and zoom the STL preview in the browser.

6. Confirm that a new `.stl` file exists in `outputs/`.

7. Switch to experimental mode and run:

```text
Make a toy car with four wheels and a cabin.
```

8. Show that template-assisted generation produced CadQuery code, preview, validation report, and a watertight STL.

9. Run an unknown/free-form prompt, for example:

```text
Make a simple trophy with a base and two handles.
```

10. Explain that unknown experimental prompts use LLM-generated CadQuery, AST safety checks, subprocess timeout, and up to two repair attempts.

11. Explain the limitation: experimental mode is research-grade and not a production CAD system.
