The previous CadQuery code failed.

User request:
{user_prompt}

Error traceback:
{traceback}

Fix the CadQuery code. Do not repeat the same broken code.
If the error mentions mirror, do not use mirror; create separate translated parts instead.
If the previous code imported cadquery at top level, move the import inside build_model().

Return only complete Python code.
No Markdown.
No explanation.

The code must define exactly:

def build_model():
    import cadquery as cq
    ...
    return model

Rules:
- The final variable must be named model.
- Do not use .mirror().
- Do not import unsafe modules.
- Do not read or write files.
- Do not execute shell commands.
