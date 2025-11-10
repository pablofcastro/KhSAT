"""
This is the AST class hierarchy for Kh
"""

from abc import ABC, abstractmethod
from S5.AST_S5 import *

class Clauses(ABC) :
    """ Class for clauses, a clauses is a sequence of Kh or not Kh formulas, without nested modalities
    """
    def __init__(self, *clauses) :
        self.clauses = clauses
    
    def __str__(self) :
        return "\n".join(map(str, self.clauses))

    def add_clause(self, clause) :
        self.clauses.append(clause)

    def accept(self, visitor, info=None) :
        for cl in self.clauses : 
            cl.accep(visitor, info)

class Kh(BinaryOperation) :
    def __str__(self):
        return f"Kh({self.left},{self.right})"

    def accept(self, visitor, info=None) :
        return visitor.visit_kh(self, info)
    
class NKh(BinaryOperation) :
    def __str__(self):
        return f"~Kh({self.left},{self.right})"

    def accept(self, visitor, info=None) :
        return visitor.visit_nkh(self, info)


