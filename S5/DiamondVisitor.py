import ast
import S5.form_visitor  as visitor


class DiamondVisitor(visitor.FormulaVisitor) :
    
    def __init__(self) :
        pass

    def visit_true(self ,cons, info) :
        return 0
    
    def visit_false(self ,cons, info) :
        return 0

    def visit_var(self, var, info) :
        return 0

    def visit_not(self, not_form, info) :
        return not_form.operand.accept(self)
    
    def visit_or(self, or_exp, info) :
        left = or_exp.left.accept(self)
        right = or_exp.right.accept(self)
        return max(left, right)
    
    def visit_and(self, and_exp, info) :
        left = and_exp.left.accept(self)
        right = and_exp.right.accept(self)
        return left+right

    def visit_diamond(self, diamond, info) :
        return diamond.operand.accept(self)+1

    def visit_box(self, box, info) :
        return box.operand.accept(self)
        result = result + 1 # each time it visits a diamons it adds 1