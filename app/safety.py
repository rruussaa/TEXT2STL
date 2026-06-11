"""AST safety checks for experimental CadQuery code."""

from __future__ import annotations

import ast


ALLOWED_IMPORTS = {"cadquery", "math"}
BLOCKED_IMPORTS = {
    "os",
    "sys",
    "subprocess",
    "pathlib",
    "socket",
    "requests",
    "shutil",
    "builtins",
}
BLOCKED_CALLS = {"open", "eval", "exec", "compile", "__import__"}
BLOCKED_ATTRIBUTES = {"mirror"}


class SafetyError(ValueError):
    """Raised when generated Python code fails the local safety checks."""


def check_code_safety(code: str) -> dict:
    errors: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {"safe": False, "errors": [f"SyntaxError: {exc}"]}

    function_names = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    if function_names != ["build_model"]:
        errors.append("Code must define exactly one top-level function named build_model.")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in BLOCKED_IMPORTS or root not in ALLOWED_IMPORTS:
                    errors.append(f"Import is not allowed: {alias.name}")

        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in BLOCKED_IMPORTS or root not in ALLOWED_IMPORTS:
                errors.append(f"Import is not allowed: {node.module}")

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_CALLS:
                errors.append(f"Call is not allowed: {node.func.id}()")

        if isinstance(node, ast.Attribute):
            if "__" in node.attr:
                errors.append(f"Dunder attributes are not allowed: {node.attr}")
            if node.attr in BLOCKED_ATTRIBUTES:
                errors.append(f"CadQuery attribute is blocked for reliability: {node.attr}()")

        if isinstance(node, ast.Name) and "__" in node.id:
            errors.append(f"Dunder names are not allowed: {node.id}")

    unique_errors = list(dict.fromkeys(errors))
    return {"safe": not unique_errors, "errors": unique_errors}


def assert_code_safe(code: str) -> None:
    result = check_code_safety(code)
    if not result["safe"]:
        raise SafetyError("; ".join(result["errors"]))
