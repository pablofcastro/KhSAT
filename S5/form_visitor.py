from abc import ABC, abstractmethod

#Visitor interface for Kh formulas

class FormulaVisitor(ABC):

    @abstractmethod
    def visit_var(self, var) :
        pass

    @abstractmethod
    def visit_or(self, conj) :
        pass

    @abstractmethod
    def visit_and(self, disj) :
        pass

    @abstractmethod
    def visit_not(self, neg) :
        pass

    @abstractmethod
    def visit_box(self, box) :
        pass

    @abstractmethod
    def visit_diamond(self, diamond) :
        pass