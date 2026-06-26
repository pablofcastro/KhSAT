"""
This is the AST class hierarchy for S5
"""

from abc import ABC, abstractmethod

# Base class for all logical formulas
class Form(ABC):

    def __eq__(self, other) :
        return str(self) == str(other)

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def accept(visitor) :
        pass


# Represents a variable, e.g., "p" or "q"
class Var(Form):
    def __init__(self, name) :
        self.name = name

    def __str__(self):
        return self.name
    
    def accept(self, visitor, info=None) :
        return visitor.visit_var(self, info)


# Represents a constant
class Constant(Form):
    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        return self.value

    def accept(self, visitor, info=None) :
        pass

class Top(Constant) :
   def __str__(self) :
       return "True"
   
   def accept(self, visitor,  info=None) :
       return visitor.visit_true(self, info)
   
class Bot(Constant) :
    def __str__(self) :
       return "False"
    
    def accept(self, visitor,  info=None) :
       return visitor.visit_false(self, info)


# Base class for unary operations
class UnaryOperation(Form):
    def __init__(self, operand):
        self.operand = operand

    def accept(self, visitor, info=None) :
        pass
       

# Unary operation 
class Not(UnaryOperation):
    def __str__(self):
        return f"not {self.operand}"

    def accept(self, visitor, info=None) :
        return visitor.visit_not(self, info)


# Unary operation for box
class Box(UnaryOperation):
    def __str__(self):
        return f"A {self.operand}"

    def accept(self, visitor, info=None) :
        return visitor.visit_box(self, info)

# Unary operation for diamond
class Diamond(UnaryOperation):
    def __str__(self):
        return f"E {self.operand}"

    def accept(self, visitor, info = None) :
        return visitor.visit_diamond(self, info)
   
   
# Base class for binary operations
class BinaryOperation(Form):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def accept(self, visitor, info = None) :
        pass


# Binary operation for and
class And(BinaryOperation):
    def __str__(self):
        return f"({self.left} & {self.right})"

    def accept(self, visitor, info=None) :
        return visitor.visit_and(self, info)

# Binary operation for or
class Or(BinaryOperation):
    def __str__(self):
        return f"({self.left} | {self.right})"

    def accept(self, visitor, info=None) :
        return visitor.visit_or(self, info)

