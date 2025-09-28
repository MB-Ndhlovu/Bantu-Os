"""
Calculator tool with safe expression evaluation.
Supports +, -, *, /, %, **, parentheses. No variables or function calls.
"""
from __future__ import annotations

import ast
import operator as op
from typing import Any

# Allowed operators
_ALLOWED_BIN_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}
_ALLOWED_UNARY_OPS = {ast.UAdd: op.pos, ast.USub: op.neg}


def _eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Num):  # type: ignore[attr-defined]
        return node.n  # type: ignore[attr-defined]
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPS:
        return _ALLOWED_UNARY_OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN_OPS:
        left = _eval(node.left)
        right = _eval(node.right)
        return _ALLOWED_BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.Expr):
        return _eval(node.value)
    raise ValueError("Unsupported expression")


def calculate(expression: str) -> Any:
    """Safely evaluate a math expression.

    Example:
        calculate("2 + 2 * 3") -> 8
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Invalid expression: {e.msg}")

    # Walk the AST to ensure only safe nodes
    for node in ast.walk(tree):
        if isinstance(node, (ast.Call, ast.Attribute, ast.Name, ast.Lambda, ast.Dict, ast.List, ast.Set, ast.comprehension)):
            raise ValueError("Disallowed syntax in expression")
    return _eval(tree.body)  # type: ignore[arg-type]
