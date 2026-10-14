"""
Suite de Pruebas Avanzada para KhSAT:
1. Tests Cromáticos DCC Complejos (Forzado de DSATUR k >= 3 y k >= 4).
2. Fuzzer Aleatorio de Fórmulas S5 (Property-Based Testing con 50 iteraciones).

Ejecutar con: python3 test_advanced_dcc_fuzzer.py
"""

import random
import traceback
import S5.AST_S5 as ast
import S5.dcc as dcc
import S5.NNFVisitor as tonnf
import S5.s5_nf as s5nf
import S5.toSAT_DCC as tosat
from S5.model_checker import S5ModelChecker
from z3 import Bool, Solver, is_and, is_true, main_ctx, sat, unknown, unsat


def solve_ast_internal(ast_node):
    """Ejecuta el pipeline completo de KhSAT y valida con S5ModelChecker."""
    nnf = ast_node.accept(tonnf.ToNNF())
    simplified = nnf.accept(s5nf.ModalCollapse())
    max_w, colors = dcc.compute_dcc_worlds(simplified)

    steps = [1, 2, 5, 12, max_w]
    bounds = sorted(list(set([b for b in steps if b <= max_w] + [max_w])))

    final_res = unknown
    final_w = max_w
    final_model = None

    for W in bounds:
        translator = tosat.ToSAT(size=W, diamond_colors=colors)
        sat_form = simplified.accept(translator, 1)

        s = Solver()
        if is_and(sat_form):
            s.add(*sat_form.children())
        else:
            s.add(sat_form)

        c_res = s.check()
        if c_res == sat:
            final_res = sat
            final_w = W
            final_model = s.model()
            break
        elif c_res == unsat:
            final_res = unsat

    model_verified = None
    if final_res == sat and final_model is not None:
        all_vars = set()

        def _get_vars(node):
            if isinstance(node, ast.Var):
                all_vars.add(node.name)
            elif isinstance(node, ast.Not):
                _get_vars(node.operand)
            elif isinstance(node, (ast.And, ast.Or)):
                _get_vars(node.left)
                _get_vars(node.right)
            elif isinstance(node, (ast.Box, ast.Diamond)):
                _get_vars(node.operand)

        _get_vars(simplified)
        explicit_worlds = list(range(1, final_w + 1))
        ctx = main_ctx()

        valuation = {}
        for w in explicit_worlds:
            for v_name in all_vars:
                z3_var = Bool(f"{v_name}@{w}", ctx)
                valuation[(v_name, w)] = is_true(final_model.eval(z3_var, model_completion=True))

        checker = S5ModelChecker(worlds=explicit_worlds, valuation=valuation, root_world=1)
        model_verified = checker.verify(simplified)

    status_str = "SAT" if final_res == sat else ("UNSAT" if final_res == unsat else "UNKNOWN")
    return status_str, model_verified, final_w, max_w


# ==============================================================================
# 1. CASOS DE PRUEBA CROMÁTICOS AVANZADOS (DCC k >= 3)
# ==============================================================================

p, q, r, s_var = ast.Var("p"), ast.Var("q"), ast.Var("r"), ast.Var("s")

# Grafo $K_3$ de diamantes incompatibles: requiere al menos 3 mundos (+1 raíz = 4)
# D(p & q) vs D(~p & q) vs D(~q)
dcc_k3 = ast.And(
    ast.Diamond(ast.And(p, q)),
    ast.And(
        ast.Diamond(ast.And(ast.Not(p), q)),
        ast.Diamond(ast.Not(q))
    )
)

# Grafo $K_4$ de diamantes incompatibles: 4 diamantes mutuamente excluyentes
# p&q, ~p&q, p&~q, ~p&~q
dcc_k4 = ast.And(
    ast.And(ast.Diamond(ast.And(p, q)), ast.Diamond(ast.And(ast.Not(p), q))),
    ast.And(ast.Diamond(ast.And(p, ast.Not(q))), ast.Diamond(ast.And(ast.Not(p), ast.Not(q))))
)

ADVANCED_DCC_TESTS = [
    ("Triángulo Incompatible K3 (Requiere W>=3)", dcc_k3, "SAT", 3),
    ("Clique Incompatible K4 (Requiere W>=4)", dcc_k4, "SAT", 4),
]


# ==============================================================================
# 2. GENERADOR ALEATORIO DE FÓRMULAS S5 (FUZZER)
# ==============================================================================

VARS = ["p", "q", "r", "s"]

def generate_random_s5_ast(depth=0, max_depth=3):
    """Genera un árbol AST aleatorio de lógica modal S5."""
    if depth >= max_depth or (depth > 0 and random.random() < 0.35):
        return ast.Var(random.choice(VARS))

    op_type = random.choice(["NOT", "AND", "OR", "BOX", "DIAMOND"])

    if op_type == "NOT":
        return ast.Not(generate_random_s5_ast(depth + 1, max_depth))
    elif op_type == "AND":
        return ast.And(
            generate_random_s5_ast(depth + 1, max_depth),
            generate_random_s5_ast(depth + 1, max_depth)
        )
    elif op_type == "OR":
        return ast.Or(
            generate_random_s5_ast(depth + 1, max_depth),
            generate_random_s5_ast(depth + 1, max_depth)
        )
    elif op_type == "BOX":
        return ast.Box(generate_random_s5_ast(depth + 1, max_depth))
    elif op_type == "DIAMOND":
        return ast.Diamond(generate_random_s5_ast(depth + 1, max_depth))


def run_advanced_suite():
    print("=" * 75)
    print(" 🎨 1. PRUEBAS DE ESTRÉS CROMÁTICO EN GRAFOS DCC (k >= 3)")
    print("=" * 75)

    for idx, (name, formula_ast, expected, min_expected_w) in enumerate(ADVANCED_DCC_TESTS, 1):
        print(f"[{idx:02d}] {name:<45} ... ", end="")
        try:
            verdict, verified, W_used, W_max = solve_ast_internal(formula_ast)
            if verdict == expected and W_max >= min_expected_w and (verdict != "SAT" or verified):
                print(f"✅ PASÓ [{verdict}] (W_opt={W_used}, W_dcc_max={W_max})")
            else:
                print(f"❌ FALLÓ (Obtenido: {verdict}, W_max={W_max}, Esperado: {expected}, min_W={min_expected_w})")
        except Exception as e:
            print(f"💥 EXCEPCIÓN: {e}")
            traceback.print_exc()

    print("\n" + "=" * 75)
    print(" 🎲 2. FUZZER STOCHÁSTICO S5 (50 Iteraciones Aleatorias)")
    print("=" * 75)

    fuzz_passed = 0
    fuzz_total = 50

    for i in range(1, fuzz_total + 1):
        # Generar fórmula aleatoria con profundidad 2 a 3
        random_formula = generate_random_s5_ast(max_depth=random.randint(2, 3))
        
        try:
            verdict, verified, W_used, W_max = solve_ast_internal(random_formula)

            if verdict == "SAT":
                if verified:
                    fuzz_passed += 1
                else:
                    print(f"  ❌ Iteración {i:02d}: FALSO POSITIVO DETECTADO (Model Checker rechazó el modelo)")
            elif verdict in ("UNSAT", "UNKNOWN"):
                fuzz_passed += 1

            if i % 10 == 0 or verdict == "SAT":
                print(f"  • Iteración {i:02d}/{fuzz_total}: Veredicto={verdict:<6} Verified={str(verified):<5} W_used={W_used}")

        except Exception as e:
            print(f"  💥 Iteración {i:02d} CRASH con error: {e}")
            traceback.print_exc()
            break

    print("\n" + "=" * 75)
    print(f" RESUMEN DE FUZZING Y PRUEBAS AVANZADAS:")
    print(f"  • Iteraciones Fuzzer Exitosas : {fuzz_passed}/{fuzz_total}")
    print("=" * 75)


if __name__ == "__main__":
    run_advanced_suite()