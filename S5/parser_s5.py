import logging
import S5.AST_S5 as ast
from lark import Lark, Transformer, v_args
logging.basicConfig(level=logging.DEBUG)

# Define the grammar for plain fuzzy formulas
grammar = """
    ?start: form
    ?form: conj
    ?conj: disj
         | conj "&" disj -> boolean_and
    
    ?disj: elem
         | disj "|" elem-> boolean_or
     
    ?elem: "~" elem -> boolean_not
         | "E" elem -> diamond
         | "A" elem -> box
         | var
         | "true" -> true
         | "false" -> false
         | "(" form ")"

    var: /[a-z_][a-z0-9_]*/   // Variable: alphanumeric starting with a letter
    %import common.CNAME
    %import common.WS
    %ignore WS
"""

# Define the grammar for intohylo formulas
intohylo_grammar = """
    ?start: "begin" form "end"

    ?form: implication

    ?implication: conjunction
                | conjunction "->" implication -> implication

    // Se conserva la precedencia original: | antes que &
    ?conjunction: disjunction
                | disjunction ("&" disjunction)+ -> intohylo_conjunction

    ?disjunction: unary
                | unary ("|" unary)+ -> intohylo_disjunction

    ?unary: "~" unary -> boolean_not
          | "<" RELATION ">" unary -> intohylo_diamond
          | "[" RELATION "]" unary -> intohylo_box
          | var
          | "true" -> true
          | "false" -> false
          | "(" form ")"

    var: /[a-z_][a-z0-9_]*/
    RELATION: /[a-zA-Z][a-zA-Z0-9_]*/

    %import common.WS
    %ignore WS
"""

@v_args(inline=True)

# we define a transformer for creating the AST
class ASTTransformer(Transformer) :
    boolean_and = ast.And
    boolean_or = ast.Or
    boolean_not = ast.Not
    box = ast.Box
    diamond = ast.Diamond
    var = ast.Var
    true = ast.Top
    false = ast.Bot

@v_args(inline=True)
class IntoHyloASTTransformer(Transformer):
    boolean_not = ast.Not
    var = ast.Var
    true = ast.Top
    false = ast.Bot

    def _balanced(self, operands, constructor):
        if len(operands) == 1:
            return operands[0]

        middle = len(operands) // 2
        return constructor(
            self._balanced(operands[:middle], constructor),
            self._balanced(operands[middle:], constructor)
        )

    def intohylo_conjunction(self, first, *rest):
        return self._balanced([first, *rest], ast.And)

    def intohylo_disjunction(self, first, *rest):
        return self._balanced([first, *rest], ast.Or)

    def intohylo_diamond(self, _relation, formula):
        return ast.Diamond(formula)

    def intohylo_box(self, _relation, formula):
        return ast.Box(formula)

    def implication(self, left, right):
        return ast.Or(ast.Not(left), right)

# Create the Lark parser instances for both grammars
plain_parser = Lark(grammar, start="start", parser="lalr")
intohylo_parser = Lark(intohylo_grammar, start="start", parser="lalr")

# a function to parse a string, it returns an AST
def parse(form, intohylo=False) :
    if intohylo:
        tree = intohylo_parser.parse(form)
        return IntoHyloASTTransformer().transform(tree)

    tree = plain_parser.parse(form)
    return ASTTransformer().transform(tree)

# some tests for testing the parser
def tests() :
    pass
 
