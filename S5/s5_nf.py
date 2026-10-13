"""
S5 Normal Form (S5-NF) Modal Collapse Visitor.
Fast 1-pass visitor simplifying adjacent nested modalities in S5:
- Box(Box(p)) -> Box(p)
- Diamond(Diamond(p)) -> Diamond(p)
- Box(Diamond(p)) -> Diamond(p)
- Diamond(Box(p)) -> Box(p)
"""

import S5.AST_S5 as ast
import S5.form_visitor as visitor


class ModalCollapse(visitor.FormulaVisitor):

    def visit_var(self, varexp, info=None):
        return varexp

    def visit_true(self, cons, info=None):
        return cons

    def visit_false(self, cons, info=None):
        return cons

    def visit_not(self, notexp, info=None):
        return ast.Not(notexp.operand.accept(self, info))

    def visit_and(self, andexp, info=None):
        operands = []
        curr = andexp
        while isinstance(curr, ast.And):
            operands.append(curr.right.accept(self, info))
            curr = curr.left
        operands.append(curr.accept(self, info))
        operands.reverse()

        res = operands[0]
        for op in operands[1:]:
            res = ast.And(res, op)
        return res

    def visit_or(self, orexp, info=None):
        operands = []
        curr = orexp
        while isinstance(curr, ast.Or):
            operands.append(curr.right.accept(self, info))
            curr = curr.left
        operands.append(curr.accept(self, info))
        operands.reverse()

        res = operands[0]
        for op in operands[1:]:
            res = ast.Or(res, op)
        return res

    def visit_box(self, boxexp, info=None):
        inner = boxexp.operand.accept(self, info)
        if isinstance(inner, (ast.Box, ast.Diamond)):
            return inner
        return ast.Box(inner)

    def visit_diamond(self, diamondexp, info=None):
        inner = diamondexp.operand.accept(self, info)
        if isinstance(inner, (ast.Box, ast.Diamond)):
            return inner
        return ast.Diamond(inner)