import S5.AST_S5 as ast
import S5.form_visitor as visitor
from z3 import *

class ToSAT(visitor.FormulaVisitor) :
    """
        class to translate a S5 formula to a z3 Boolean formula
    """
    def __init__(self, size) :
        self.size = size
        self.result = {} # a dictionary to save the results and avoid computing twice the same thing, this is used only in the case of E, A

    def visit_var(self ,varexp, info) :
        if info is not  None : 
            result = Bool(str(varexp)+"@"+str(info))
        else :
            result = Bool(str(varexp))
        return result
    
    def visit_not(self, notexp, info) :
        return Not(notexp.operand.accept(self, info)) 

    def visit_and(self, andexp, info) :
        left = andexp.left.accept(self, info)
        right = andexp.right.accept(self, info)
        return And([left, right])

    def visit_or(self, orexp, info) :
        left = orexp.left.accept(self, info)
        right = orexp.right.accept(self, info)
        return  Or([left, right])

    def visit_box(self, boxexp, info) :
        if str(boxexp) in self.result  : # we save the result here to avoid computing twice
            return self.result[str(boxexp)]
        else :
            subform = boxexp.operand
            subforms = [ subform.accept(self, i+1) for i in range(self.size) ]
            self.result[str(boxexp)] = And(subforms)
            return self.result[str(boxexp)]

    def visit_diamond(self, diamondexp, info) :
        if str(diamondexp) in self.result  :
            return self.result[str(diamondexp)]
        else :
            subform = diamondexp.operand
            subforms = [ subform.accept(self, i+1) for i in range(self.size) ]
            self.result[str(diamondexp)] = Or(subforms)
            return self.result[str(diamondexp)]
    
