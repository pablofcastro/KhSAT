#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path

from lark.exceptions import UnexpectedInput

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

import S5.AST_S5 as ast
import S5.parser_s5 as s5parser


def validate_relation(value):
    if not re.fullmatch(r"r\d+", value):
        raise argparse.ArgumentTypeError(
            "relation must be an IntoHylo label such as r1"
        )
    return value


def _to_intohylo(node, variables, relation):
    if isinstance(node, ast.Var):
        if node.name not in variables:
            variables[node.name] = f"p{len(variables) + 1}"
        return variables[node.name]
    if isinstance(node, ast.Top):
        return "true"
    if isinstance(node, ast.Bot):
        return "false"
    if isinstance(node, ast.Not):
        return f"~{_to_intohylo(node.operand, variables, relation)}"
    if isinstance(node, ast.Box):
        return f"[{relation}] {_to_intohylo(node.operand, variables, relation)}"
    if isinstance(node, ast.Diamond):
        return f"<{relation}> {_to_intohylo(node.operand, variables, relation)}"
    if isinstance(node, ast.And):
        left = _to_intohylo(node.left, variables, relation)
        right = _to_intohylo(node.right, variables, relation)
        return f"({left} & {right})"
    if isinstance(node, ast.Or):
        left = _to_intohylo(node.left, variables, relation)
        right = _to_intohylo(node.right, variables, relation)
        return f"({left} | {right})"
    raise TypeError(f"Unsupported formula node: {type(node).__name__}")


def _ast_signature(node, variable_names=None):
    """Return a structural representation, optionally renaming variables."""
    if isinstance(node, ast.Var):
        name = node.name
        if variable_names is not None:
            name = variable_names.get(name, name)
        return (ast.Var, name)
    if isinstance(node, (ast.Top, ast.Bot)):
        return (type(node),)
    if isinstance(node, (ast.Not, ast.Box, ast.Diamond)):
        return (type(node), _ast_signature(node.operand, variable_names))
    if isinstance(node, (ast.And, ast.Or)):
        return (
            type(node),
            _ast_signature(node.left, variable_names),
            _ast_signature(node.right, variable_names),
        )
    raise TypeError(f"Unsupported formula node: {type(node).__name__}")


def translate_formula(text, relation="r1"):
    """Translate to IntoHylo and verify the generated AST matches the input."""
    if not re.fullmatch(r"r\d+", relation):
        raise ValueError("relation must be an IntoHylo label such as r1")

    formula_ast = s5parser.parse(text)
    variables = {}
    translated = _to_intohylo(formula_ast, variables, relation)
    result = f"begin {translated} end\n"

    original_names = {into_name: source_name for source_name, into_name in variables.items()}
    try:
        translated_ast = s5parser.parse(result, intohylo=True)
    except UnexpectedInput as exc:
        raise ValueError(
            "round-trip validation failed: generated formula is not valid IntoHylo"
        ) from exc

    if _ast_signature(formula_ast) != _ast_signature(translated_ast, original_names):
        raise ValueError(
            "round-trip validation failed: translated formula differs from input"
        )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Translate an S5 formula file to IntoHylo format."
    )
    parser.add_argument("input", type=Path, help="file containing an S5 formula")
    parser.add_argument("output", type=Path, help="destination IntoHylo file")
    parser.add_argument(
        "--relation",
        type=validate_relation,
        default="r1",
        help="IntoHylo relation label for modal operators (default: r1)",
    )
    args = parser.parse_args()

    try:
        source = args.input.read_text(encoding="utf-8")
    except OSError as exc:
        parser.error(f"cannot read input file {args.input}: {exc}")

    try:
        result = translate_formula(source, args.relation)
    except UnexpectedInput as exc:
        parser.error(f"invalid S5 formula in {args.input}:\n{exc}")
    except ValueError as exc:
        parser.error(str(exc))

    try:
        args.output.write_text(result, encoding="utf-8")
    except OSError as exc:
        parser.error(f"cannot write output file {args.output}: {exc}")

    print(f"Generated: {args.output}")


if __name__ == "__main__":
    main()
