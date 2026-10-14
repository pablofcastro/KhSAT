"""
S5 to Z3 propositional translator using DCC compressed world universe bounds.
"""

import S5.AST_S5 as ast
import S5.form_visitor as visitor
from z3 import Bool, BoolRef, BoolVal, main_ctx, z3core


def fast_and(args, ctx=None):
    if not args:
        return BoolVal(True, ctx=ctx)
    if len(args) == 1:
        return args[0]
    ctx = main_ctx() if ctx is None else ctx
    sz = len(args)
    _args = (z3core.Ast * sz)()
    for i, a in enumerate(args):
        _args[i] = a.as_ast()
    return BoolRef(z3core.Z3_mk_and(ctx.ref(), sz, _args), ctx)


def fast_or(args, ctx=None):
    if not args:
        return BoolVal(False, ctx=ctx)
    if len(args) == 1:
        return args[0]
    ctx = main_ctx() if ctx is None else ctx
    sz = len(args)
    _args = (z3core.Ast * sz)()
    for i, a in enumerate(args):
        _args[i] = a.as_ast()
    return BoolRef(z3core.Z3_mk_or(ctx.ref(), sz, _args), ctx)


def fast_not(arg, ctx=None):
    ctx = main_ctx() if ctx is None else ctx
    return BoolRef(z3core.Z3_mk_not(ctx.ref(), arg.as_ast()), ctx)


class ToSAT(visitor.FormulaVisitor):

    def __init__(self, size, diamond_colors=None):
        self.size = size
        self.diamond_colors = diamond_colors if diamond_colors else {}
        self.modal_cache = {}
        self.var_cache = {}
        self.ctx = main_ctx()

    def visit_var(self, varexp, info=None):
        name = varexp.name
        key = (name, info)
        if key in self.var_cache:
            return self.var_cache[key]
        res = (
            Bool(f"{name}@{info}", self.ctx)
            if info is not None
            else Bool(name, self.ctx)
        )
        self.var_cache[key] = res
        return res

    def visit_true(self, cons, info=None):
        return BoolVal(True, ctx=self.ctx)

    def visit_false(self, cons, info=None):
        return BoolVal(False, ctx=self.ctx)

    def visit_not(self, notexp, info=None):
        child = notexp.operand.accept(self, info)
        return fast_not(child, self.ctx)

    def visit_and(self, andexp, info=None):
        operands = []
        curr = andexp
        while isinstance(curr, ast.And):
            operands.append(curr.right.accept(self, info))
            curr = curr.left
        operands.append(curr.accept(self, info))
        operands.reverse()
        return fast_and(operands, self.ctx)

    def visit_or(self, orexp, info=None):
        operands = []
        curr = orexp
        while isinstance(curr, ast.Or):
            operands.append(curr.right.accept(self, info))
            curr = curr.left
        operands.append(curr.accept(self, info))
        operands.reverse()
        return fast_or(operands, self.ctx)

    def visit_box(self, boxexp, info=None):
        nodo_id = id(boxexp)
        if nodo_id in self.modal_cache:
            return self.modal_cache[nodo_id]

        subform = boxexp.operand
        subforms = [subform.accept(self, i + 1) for i in range(self.size)]
        res = fast_and(subforms, self.ctx)
        self.modal_cache[nodo_id] = res
        return res

    def visit_diamond(self, diamondexp, info=None):
        nodo_id = id(diamondexp)
        if nodo_id in self.modal_cache:
            return self.modal_cache[nodo_id]

        subform = diamondexp.operand
        subforms = [subform.accept(self, i + 1) for i in range(self.size)]
        res = fast_or(subforms, self.ctx)

        self.modal_cache[nodo_id] = res
        return res