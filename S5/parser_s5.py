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
         | "(" form ")"

    var: /[a-z_][a-z0-9_]*/   // Variable: alphanumeric starting with a letter
    %import common.CNAME
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

# a function to parse a string, it returns an AST
def parse(form) :
    parser = Lark(grammar, start='start', parser='lalr',  debug=True)
    tree = parser.parse(form)
    return ASTTransformer().transform(tree)
    #fuzzy_parser = Lark(grammar, start='start', parser='lalr',  debug=True)
    #tree = fuzzy_parser.parse(form)
    #return ASTTransformer().transform(tree)

# some tests for testing the parser
def tests() :
    pass
 #   form1 = "x or y"
 #   form2 = "x"
 #   form3 = "x limplies (x lor y)"
 #   form4 = "x por ((x max z) min z)"
 #   form5 = "0.56 lor x"
#
#    fuzzy_parser = Lark(grammar, start='start', parser='lalr',  debug=True)
#    fparser = Lark(grammar, start='start', parser='lalr',  debug=True)
#   tree1 = fuzzy_parser.parse(form1)
#    print(ASTTransformer().transform(tree1))
#    tree2 = fuzzy_parser.parse(form2)
#    print(ASTTransformer().transform(tree2))
#    tree3 = fuzzy_parser.parse(form3)
#    print(ASTTransformer().transform(tree3))
#    tree4 = fuzzy_parser.parse(form4)
#    print(ASTTransformer().transform(tree4))
#    tree5 = fuzzy_parser.parse(form5)
#    print(ASTTransformer().transform(tree5))
