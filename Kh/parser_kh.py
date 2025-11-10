import logging
import Kh.AST_kh as ast
from lark import Lark, Transformer, v_args
logging.basicConfig(level=logging.DEBUG)

# Define the grammar for plain fuzzy formulas
grammar = """
    ?start: kh_seq
    ?kh_seq: kh (";" kh)* -> clauses
    ?kh: "Kh(" form "," form ")" -> kh
        | "~" "Kh("  form "," form ")" -> nkh
    ?form: conj
    ?conj: disj
         | conj "&" disj -> boolean_and
    
    ?disj: elem
         | disj "|" elem-> boolean_or
     
    ?elem: "~" elem -> boolean_not
         | var
         | "true" -> true
         | "false" -> false
         | "(" form ")"

    var: /[a-z_][a-z0-9_]*/   // Variable: alphanumeric starting with a letter
    %import common.CNAME
    %import common.WS
    %ignore WS
"""

@v_args(inline=True)

# we define a transformer for creating the AST
class ASTTransformer(Transformer) :
    clauses = ast.Clauses
    kh = ast.Kh
    nkh = ast.NKh
    boolean_and = ast.And
    boolean_or = ast.Or
    boolean_not = ast.Not
    var = ast.Var
    true = ast.Top
    false = ast.Bot

# a function to parse a string, it returns an AST
def parse(form) :
    parser = Lark(grammar, start='start', parser='lalr',  debug=True)
    tree = parser.parse(form)
    return ASTTransformer().transform(tree)
  
# some tests for testing the parser
def tests() :
    pass
 