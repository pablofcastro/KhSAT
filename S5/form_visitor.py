from abc import ABC, abstractmethod

#Visitor interface for Kh formulas

class FormulaVisitor(ABC):

    @abstractmethod
    def visit_var(self, var, info) :
        pass

    @abstractmethod
    def visit_or(self, conj, info) :
        pass

    @abstractmethod
    def visit_and(self, disj, info) :
        pass

    @abstractmethod
    def visit_not(self, neg, info) :
        pass

    @abstractmethod
    def visit_box(self, box, info) :
        pass

    @abstractmethod
    def visit_diamond(self, diamond, info) :
        pass