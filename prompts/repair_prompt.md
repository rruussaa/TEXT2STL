The previous CadQuery code failed.

User request:
{user_prompt}

Error traceback:
{traceback}

Fix the CadQuery code. Do not repeat the same broken code.
If the error mentions mirror, do not use mirror; create separate translated parts instead.
If the previous code imported cadquery at top level, move the import inside build_model().
If the error says build_model is missing, return complete Python code that starts with def build_model().
If the error mentions STL validation, watertightness, zero volume, or printer bounds, change the geometry so the exported model is one valid solid.
For joined body parts, make parts overlap meaningfully before unioning them, or use one continuous base solid with added features.
Avoid barely touching solids, separated floating parts, open shells, and surface-only geometry.
Prefer simple boxes, cylinders, spheres, lofts, and unions that create a single watertight printable object.
For human/person prompts, prefer a stylized blocky figure: torso box, head box or sphere embedded into the torso, two arm boxes overlapping the shoulders, two leg boxes overlapping the torso.

Return only complete Python code.
No Markdown.
No explanation.
Do not include thinking text, comments before the code, or Markdown fences.

The code must define exactly:

def build_model():
    import cadquery as cq
    ...
    return model

Rules:
- Define build_model() at top level. If helper logic is needed, define helper functions above it.
- The final variable must be named model.
- Do not use .mirror().
- Do not import unsafe modules.
- Do not read or write files.
- Do not execute shell commands.
