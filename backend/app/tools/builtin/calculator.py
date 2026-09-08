"""Secure mathematical calculation tool using AST-based evaluation."""

import ast
import math
import operator
from typing import Any

from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.tools.permissions import PermissionLevel


class CalculatorArgs(BaseModel):
    """Input arguments for the calculator tool."""

    expression: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="A mathematical expression to safely evaluate (e.g. '2 + 2', '(10 * 5) / 2', '2 ** 8')",
    )


class SafeMathEvaluator:
    """Explicitly whitelisted AST-based arithmetic evaluator.

    Strictly forbids:
    - Function calls
    - Attribute access
    - Variable / identifier lookup
    - Imports and statement blocks
    """

    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    MAX_EXPONENT = 1000
    MAX_BASE = 1_000_000

    @classmethod
    def evaluate(cls, expression: str) -> int | float:
        """Parse and evaluate an arithmetic expression safely without eval() or exec()."""
        cleaned = expression.strip()
        if not cleaned:
            raise ValueError("Expression cannot be empty.")

        try:
            tree = ast.parse(cleaned, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Invalid mathematical syntax: {exc.msg}")

        return cls._eval_node(tree.body)

    @classmethod
    def _eval_node(cls, node: ast.AST) -> int | float:
        """Recursively evaluate only whitelisted AST nodes."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_OPERATORS:
                raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)

            # Guard against exponentiation denial of service
            if op_type is ast.Pow:
                if abs(right) > cls.MAX_EXPONENT:
                    raise ValueError(f"Exponent exceeds safety limit ({cls.MAX_EXPONENT}).")
                if abs(left) > cls.MAX_BASE and right > 10:
                    raise ValueError("Base value too large for exponentiation.")

            # Guard against division by zero
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ValueError("Division by zero.")

            handler = cls.ALLOWED_OPERATORS[op_type]
            try:
                result = handler(left, right)
                if isinstance(result, complex):
                    raise ValueError("Complex numbers are not supported.")
                return result
            except OverflowError:
                raise ValueError("Arithmetic calculation resulted in numerical overflow.")

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            operand = cls._eval_node(node.operand)
            return cls.ALLOWED_OPERATORS[op_type](operand)

        # Explicit rejection of non-whitelisted nodes
        elif isinstance(node, ast.Call):
            raise ValueError("Function calls are strictly forbidden in calculator expressions.")
        elif isinstance(node, ast.Attribute):
            raise ValueError("Attribute access is strictly forbidden in calculator expressions.")
        elif isinstance(node, ast.Name):
            raise ValueError(f"Variable or identifier access '{node.id}' is strictly forbidden.")
        else:
            raise ValueError(f"Unsupported expression element: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """Tool providing safe mathematical computation."""

    name = "calculator"
    description = (
        "Safely evaluate basic mathematical expressions. "
        "Supports addition (+), subtraction (-), multiplication (*), division (/), "
        "modulus (%), exponentiation (**), and parentheses. Does not allow code or variables."
    )
    permission_level = PermissionLevel.READ
    args_model = CalculatorArgs

    async def execute(self, expression: str, **kwargs: Any) -> int | float:
        """Execute the mathematical expression and return the evaluated number."""
        return SafeMathEvaluator.evaluate(expression)

    def verify(self, result: Any) -> bool:
        """Verify that the result is a finite numeric value."""
        if not isinstance(result, (int, float)):
            return False
        return not (math.isnan(result) or math.isinf(result))
