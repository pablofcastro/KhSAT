"""
Main solver pipeline for S5 formulas with DCC integration, 
S5-NF Simplification, and Incremental World Bound (IWB).
"""

import argparse
import os
import sys
import time

import S5.dcc as dcc
import S5.NNFVisitor as tonnf
import S5.parser_s5 as s5parser
import S5.s5_nf as s5nf
import S5.toSAT_DCC as tosat
from S5.model_checker import S5ModelChecker
from z3 import Bool, Solver, is_and, is_true, main_ctx, sat, unsat

sys.setrecursionlimit(100000)
verbose = False


def validate_file(f):
    if not os.path.exists(f):
        raise argparse.ArgumentTypeError(f"Couldn't find {f}.")
    return f


def get_all_atomic_vars(node):
    """Extracts all atomic variable names from the AST."""
    vars_set = set()
    if isinstance(node, s5parser.ast.Var):
        vars_set.add(node.name)
    elif isinstance(node, s5parser.ast.Not):
        vars_set.update(get_all_atomic_vars(node.operand))
    elif isinstance(node, (s5parser.ast.And, s5parser.ast.Or)):
        vars_set.update(get_all_atomic_vars(node.left))
        vars_set.update(get_all_atomic_vars(node.right))
    elif isinstance(node, (s5parser.ast.Box, s5parser.ast.Diamond)):
        vars_set.update(get_all_atomic_vars(node.operand))
    return vars_set


def satS5(formula, intohylo=False, enable_iwb=True):
    overall_start = time.perf_counter()

    # 1. Parse formula
    t0 = time.perf_counter()
    parsed_form = s5parser.parse(formula, intohylo=intohylo)
    parse_time = time.perf_counter() - t0

    # 2. Transform to Negation Normal Form (NNF) & Modal Collapse
    t1 = time.perf_counter()
    nnf_visitor = tonnf.ToNNF()
    nnf_form = parsed_form.accept(nnf_visitor)

    collapse_visitor = s5nf.ModalCollapse()
    simplified_nnf = nnf_form.accept(collapse_visitor)
    nnf_time = time.perf_counter() - t1

    # 3. Compute DCC max world bound
    t2 = time.perf_counter()
    max_dcc_worlds, diamond_colors = dcc.compute_dcc_worlds(simplified_nnf)
    dcc_calc_time = time.perf_counter() - t2

    # 4. Incremental World Bound (IWB) strategy setup
    if enable_iwb and max_dcc_worlds > 15:
        # Secuencia incremental: inicia pequeño y escala progresivamente hasta max_dcc_worlds
        steps = [5, 12, 25, 50, 100, 180, max_dcc_worlds]
        bounds_to_try = [b for b in steps if b < max_dcc_worlds] + [max_dcc_worlds]
    else:
        bounds_to_try = [max_dcc_worlds]

    res = unsat
    final_worlds_used = max_dcc_worlds
    final_z3_model = None
    total_z3_time = 0.0
    total_sat_trans_time = dcc_calc_time

    # 5. Incremental Solving Loop
    for current_W in bounds_to_try:
        t_trans = time.perf_counter()
        sat_visitor = tosat.ToSAT(size=current_W, diamond_colors=diamond_colors)
        boolean_form = simplified_nnf.accept(sat_visitor, 1)
        total_sat_trans_time += (time.perf_counter() - t_trans)

        s = Solver()
        if is_and(boolean_form):
            s.add(*boolean_form.children())
        else:
            s.add(boolean_form)

        z3_start = time.perf_counter()
        check_res = s.check()
        iter_z3_time = time.perf_counter() - z3_start
        total_z3_time += iter_z3_time

        if check_res == sat:
            res = sat
            final_worlds_used = current_W
            final_z3_model = s.model()
            break  # Éxito: encontramos un modelo en un universo pequeño

    overall_time = time.perf_counter() - overall_start

    # 6. Model Verification for SAT
    if res == sat and final_z3_model is not None:
        all_vars = get_all_atomic_vars(simplified_nnf)
        worlds_list = list(range(1, final_worlds_used + 1))
        ctx = main_ctx()

        valuation = {}
        for w in worlds_list:
            for v_name in all_vars:
                z3_var = Bool(f"{v_name}@{w}", ctx)
                eval_res = final_z3_model.eval(z3_var, model_completion=True)
                valuation[(v_name, w)] = is_true(eval_res)

        explicit_worlds = list(range(1, final_worlds_used + 1))
        checker = S5ModelChecker(
            worlds=explicit_worlds,
            valuation=valuation,
            root_world=1
        )
        is_valid_model = checker.verify(simplified_nnf)

        if is_valid_model:
            print("[Model Checker: VERIFIED ✅]")
        else:
            print("[Model Checker: FAILED ❌]")

    print("The formula is " + ("SAT." if res == sat else "unsat."))
    print(f"DCC Worlds: {final_worlds_used} (Max limit: {max_dcc_worlds})")
    print(f"Parse time: {parse_time:.6f}")
    print(f"NNF/Simplify time: {nnf_time:.6f}")
    print(f"To SAT time: {total_sat_trans_time:.6f}")
    print(f"Z3 time: {total_z3_time:.6f}")
    print(f"Total time: {overall_time:.6f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S5 Modal Logic Solver with DCC & IWB")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-f", "--file", dest="file", type=validate_file, metavar="FILE")
    parser.add_argument("--intohylo", action="store_true")
    parser.add_argument("-i", "--inline", dest="form", metavar="FORMULA")
    args = parser.parse_args()

    if args.verbose:
        verbose = True
    if args.form:
        satS5(args.form, intohylo=args.intohylo)
    elif args.file:
        with open(args.file, "r") as f:
            satS5(f.read(), intohylo=args.intohylo)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)