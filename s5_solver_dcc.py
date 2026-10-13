"""
Main solver pipeline for S5 formulas with DCC integration and S5-NF Simplification.
"""

import argparse
import S5.AST_S5 as ast
import os
import sys
import time

# Incorporamos el nuevo optimizador
import S5.s5_nf as s5nf
import S5.dcc as dcc
import S5.NNFVisitor as tonnf
import S5.parser_s5 as s5parser
import S5.toSAT_DCC as tosat
from z3 import Solver, is_and, sat

from S5.model_checker import S5ModelChecker

# Aumentar drásticamente para árboles sintácticos inmensos
sys.setrecursionlimit(100000)

verbose = False

def get_all_atomic_vars(node):
    """Extrae todos los nombres de variables atómicas presentes en el AST."""
    vars_set = set()
    if isinstance(node, ast.Var):
        vars_set.add(node.name)
    elif isinstance(node, ast.Not):
        vars_set.update(get_all_atomic_vars(node.operand))
    elif isinstance(node, (ast.And, ast.Or)):
        vars_set.update(get_all_atomic_vars(node.left))
        vars_set.update(get_all_atomic_vars(node.right))
    elif isinstance(node, (ast.Box, ast.Diamond)):
        vars_set.update(get_all_atomic_vars(node.operand))
    return vars_set


def validate_file(f):
    if not os.path.exists(f):
        raise argparse.ArgumentTypeError(f"Couldn't find {f}.")
    return f

def satS5(formula, intohylo=False, verbose=verbose):
    overall_start = time.perf_counter()

    # 1. Parse formula
    t0 = time.perf_counter()
    parsed_form = s5parser.parse(formula, intohylo=intohylo)
    parse_time = time.perf_counter() - t0

    # 2. Transform to Negation Normal Form (NNF)
    t1 = time.perf_counter()
    nnf_visitor = tonnf.ToNNF()
    nnf_form = parsed_form.accept(nnf_visitor)
    
    # 3. Collapse adjacent modalities
    collapse_visitor = s5nf.ModalCollapse()
    simplified_nnf = nnf_form.accept(collapse_visitor)
    nnf_time = time.perf_counter() - t1

    # 4. Compute DCC graph coloring and reduced world bound
    t2 = time.perf_counter()
    # Usamos la formula simplificada
    dcc_worlds, diamond_colors = dcc.compute_dcc_worlds(simplified_nnf)

    # 5. Translate modal formula to Z3 propositional representation
    sat_visitor = tosat.ToSAT(size=dcc_worlds, diamond_colors=diamond_colors)
    boolean_form = simplified_nnf.accept(sat_visitor, 1)
    to_sat_time = time.perf_counter() - t2

    translation_time = time.perf_counter() - overall_start

    # 6. Execute Z3 Solver
    s = Solver()
    if is_and(boolean_form):
        s.add(*boolean_form.children())
    else:
        s.add(boolean_form)

    z3_start = time.perf_counter()
    res = s.check()
    z3_time = time.perf_counter() - z3_start
    overall_time = time.perf_counter() - overall_start

    if res == sat:
        z3_model = s.model()

        # 1. Extraer todas las variables atómicas de la fórmula y los mundos activos
        all_vars = get_all_atomic_vars(simplified_nnf)
        worlds_list = list(range(1, dcc_worlds + 1))

        # 2. Completar la valuación consultando a Z3 con model_completion=True
        from z3 import Bool, main_ctx, is_true
        ctx = main_ctx()
        
        valuation = {}
        for w in worlds_list:
            for v_name in all_vars:
                z3_var = Bool(f"{v_name}@{w}", ctx)
                # evalua la variable en el modelo de Z3 forzando una asignación consistente
                eval_res = z3_model.eval(z3_var, model_completion=True)
                valuation[(v_name, w)] = is_true(eval_res)

        if verbose:
            print("=== EXTRACTED COMPLETE VALUATION ===")
            for (var, w), val in sorted(valuation.items()):
                print(f"  World {w}: {var} = {val}")
            print("===================================\n")

        # 3. Verificar el modelo Kripke completo
        checker = S5ModelChecker(
            worlds_count=dcc_worlds, valuation=valuation, root_world=1
        )
        is_valid_model = checker.verify(simplified_nnf)

        if is_valid_model:
            print("[Model Checker: VERIFIED ✅]")
        else:
            print("[Model Checker: FAILED ❌]")

    print("The formula is " + ("SAT." if res == sat else "unsat."))
    print(f"DCC Worlds: {dcc_worlds}")
    print(f"Parse time: {parse_time:.6f}")
    print(f"NNF/Simplify time: {nnf_time:.6f}")
    print(f"To SAT time: {to_sat_time:.6f}")
    print(f"Translation time: {translation_time:.6f}")
    print(f"Z3 time: {z3_time:.6f}")
    print(f"Total time: {overall_time:.6f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S5 Modal Logic Solver with DCC")
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-f", "--file", dest="file", type=validate_file, help="the file with the formula", metavar="FILE")
    parser.add_argument("--intohylo", action="store_true", help="interprets diamonds as <r1> and boxes as [r1]")
    parser.add_argument("-i", "--inline", dest="form", help="takes a formula as inline input", metavar="FORMULA")
    args = parser.parse_args()

    if args.verbose:
        verbose = True
    if args.form:
        problem = args.form
        satS5(problem, intohylo=args.intohylo, verbose=verbose)
    elif args.file:
        file_name = args.file
        with open(file_name, "r") as file:
            problem = file.read()
            satS5(problem, intohylo=args.intohylo, verbose=verbose)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)