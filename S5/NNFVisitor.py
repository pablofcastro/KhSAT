import S5.AST_S5 as ast
import S5.form_visitor as visitor

class ToNNF(visitor.FormulaVisitor) :
    
    def __init__(self) :
        self.result = {} # a dictionary to avoid computing twice the same subformula

    def visit_var(self, var, info) :
        return var
    
    def visit_true(self ,cons, info) :
        return cons
    
    def visit_false(self ,cons, info) :
        return cons
    
    def visit_not(self, not_exp, info) :
        if id(not_exp) in self.result :
            return self.result[id(not_exp)] 
        else :
            subform = not_exp.operand
            if (isinstance(subform, ast.Var)) : # var case
                self.result[id(not_exp)] = not_exp
                #return not_exp
            elif (isinstance(subform, ast.Top)) :
                self.result[id(not_exp)] = ast.Bot()
            elif (isinstance(subform, ast.Bot)) :
                self.result[id(not_exp)] = ast.Top()
            elif (isinstance(subform, ast.Not)) : # not case
                #return ast.Not(not_exp.operand.accept(self)) 
                self.result[id(not_exp)] = subform.operand.accept(self) # !! p = p
                #self.result[str(not_exp)] = ast.Not(not_exp.operand.accept(self)) 
            elif (isinstance(subform, ast.And)) : # and case
                left = ast.Not(subform.left)
                right = ast.Not(subform.right)
                #self.result[str(not_exp)] = ast.Or(subform.left.accept(self), subform.right.accept(self))
                self.result[id(not_exp)] = ast.Or(left.accept(self), right.accept(self))
                #return new_form
            elif (isinstance(subform, ast.Or)) :   # or case
                left = ast.Not(subform.left)
                right = ast.Not(subform.right)
                self.result[id(not_exp)] = ast.And(left.accept(self), right.accept(self))
                #return new_form
            elif (isinstance(subform, ast.Box)) :   # box case  
                operand = ast.Not(subform.left)
                self.result[id(not_exp)] = ast.Diamond(operand.accept(self))
                #self.result[str(not_exp)] = ast.Diamond(subform.left.accept(self))
                #self.result[str(not_exp)] = ast.Diamond(subform.left.accept(self))
                #return new_form
            elif (isinstance(subform, ast.Diamond)) :  #  diamond case
                operand = ast.Not(subform.left)
                self.result[id(not_exp)] = ast.Box(operand.accept(self))
                #self.result[str(not_exp)] = ast.Box(subform.left.accept(self))
                #return new_form
            return self.result[id(not_exp)]
        
    def visit_and(self, and_exp, info) :
        if id(and_exp) in self.result :
            return self.result[id(and_exp)]
        else :
            self.result[id(and_exp)] = ast.And(and_exp.left.accept(self), and_exp.right.accept(self))
            return self.result[id(and_exp)]
    
    def visit_or(self, or_exp, info) :
        if id(or_exp) in self.result :
            return self.result[id(or_exp)]
        else :
            self.result[id(or_exp)] = ast.Or(or_exp.left.accept(self), or_exp.right.accept(self))
            return self.result[id(or_exp)]
        
    def visit_box(self, box_exp, info) :
        if id(box_exp) in self.result :
            return self.result[id(box_exp)]
        else :
            self.result[id(box_exp)] = ast.Box(box_exp.operand.accept(self))
        return self.result[id(box_exp)]
    
    def visit_diamond(self, diamond_exp, info) :
        if id(diamond_exp) in self.result :
            return self.result[id(diamond_exp)]
        else :
            self.result[id(diamond_exp)] = ast.Diamond(diamond_exp.operand.accept(self))
            return self.result[id(diamond_exp)]