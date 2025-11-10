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
        if str(not_exp) in self.result :
            return self.result[str(not_exp)] 
        else :
            subform = not_exp.operand
            if (isinstance(subform, ast.Var)) : # var case
                self.result[str(not_exp)] = not_exp
                #return not_exp
            elif (isinstance(subform, ast.Top)) :
                self.result[str(not_exp)] = ast.Bot()
            elif (isinstance(subform, ast.Bot)) :
                self.result[str(not_exp)] = ast.Top()
            elif (isinstance(subform, ast.Not)) : # not case
                #return ast.Not(not_exp.operand.accept(self)) 
                self.result[str(not_exp)] = ast.Not(not_exp.operand.accept(self)) 
            elif (isinstance(subform, ast.And)) : # and case
                self.result[str(not_exp)] = ast.Or(subform.left.accept(self), subform.right.accept(self))
                #return new_form
            elif (isinstance(subform, ast.Or)) :   # or case
                self.result[str(not_exp)] = ast.And(subform.left.accept(self), subform.right.accept(self))
                #return new_form
            elif (isinstance(subform, ast.Box)) :   # box case  
                self.result[str(not_exp)] = ast.Diamond(subform.left.accept(self))
                #return new_form
            elif (isinstance(subform, ast.Diamond)) :  #  diamond case
                self.result[str(not_exp)] = ast.Box(subform.left.accept(self))
                #return new_form
            return self.result[str(not_exp)]
        
    def visit_and(self, and_exp, info) :
        if str(and_exp) in self.result :
            return self.result[str(and_exp)]
        else :
            self.result[str(and_exp)] = ast.And(and_exp.left.accept(self), and_exp.right.accept(self))
            return self.result[str(and_exp)]
    
    def visit_or(self, or_exp, info) :
        if str(or_exp) in self.result :
            return self.result[str(or_exp)]
        else :
            self.result[str(or_exp)] = ast.Or(or_exp.left.accept(self), or_exp.right.accept(self))
            return self.result[str(or_exp)]
        
    def visit_box(self, box_exp, info) :
        if str(box_exp) in self.result :
            return self.result[str(box_exp)]
        else :
            self.result[str(box_exp)] = ast.Box(box_exp.operand.accept(self))
        return self.result[str(box_exp)]
    
    def visit_diamond(self, diamond_exp, info) :
        if str(diamond_exp) in self.result :
            return self.result[str(diamond_exp)]
        else :
            self.result[str(diamond_exp)] = ast.Diamond(diamond_exp.operand.accept(self))
            return self.result[str(diamond_exp)]