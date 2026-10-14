"""
Suite de Pruebas Extrema y Casos Borde para KhSAT (S5 Solver & Model Checker).
Ejecutar con: python3 test_khsat_suite.py
"""

import traceback
import S5.AST_S5 as ast
import S5.dcc as dcc
import S5.NNFVisitor as tonnf
import S5.s5_nf as s5nf
import S5.toSAT_DCC as tosat
from S5.model_checker import S5ModelChecker
from z3 import Bool, Solver, is_and, is_true, main_ctx, sat, unsat, unknown


def solve_formula_internal(ast_node):
    """
    Ejecuta el pipeline interno de KhSAT sobre un nodo AST
    y devuelve el veredicto ('SAT', 'UNSAT', 'UNKNOWN') y la verificación del Model Checker.
    """
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
    return status_str, model_verified, final_w


# ==============================================================================
# DEFINICIÓN DE CASOS DE PRUEBA EN AST DIRECTO
# ==============================================================================

p, q, r = ast.Var("p"), ast.Var("q"), ast.Var("r")

TEST_CASES = [
    # --- 1. PROPOSICIONAL BÁSICO Y CONSTANTES ---
    ("Proposicional Trivial SAT", p, "SAT"),
    ("Contradicción Clásica", ast.And(p, ast.Not(p)), "UNSAT"),
    ("Tautología Proposicional", ast.Or(p, ast.Not(p)), "SAT"),
    ("Constante Top", ast.Top(), "SAT"),
    ("Constante Bot", ast.Bot(), "UNSAT"),
    ("Simplificación con Top", ast.And(p, ast.Top()), "SAT"),
    ("Simplificación con Bot", ast.And(p, ast.Bot()), "UNSAT"),

    # --- 2. AXIOMAS Y TEOREMAS FUNDAMENTALES DE S5 ---
    # Negación de Axioma K: ~(Box(p -> q) -> (Box(p) -> Box(q))) => Box(Not(p) | q) & Box(p) & Diamond(Not(q))
    ("Axioma K (Violación)", ast.And(ast.Box(ast.Or(ast.Not(p), q)), ast.And(ast.Box(p), ast.Diamond(ast.Not(q)))), "UNSAT"),

    # Negación de Axioma T: ~(Box(p) -> p) => Box(p) & Not(p)
    ("Axioma T - Reflexividad (Violación)", ast.And(ast.Box(p), ast.Not(p)), "UNSAT"),

    # Negación de Axioma 4: ~(Box(p) -> Box(Box(p))) => Box(p) & Diamond(Not(p))
    ("Axioma 4 - Transitividad (Violación)", ast.And(ast.Box(p), ast.Diamond(ast.Not(p))), "UNSAT"),

    # Negación de Axioma 5: ~(Diamond(p) -> Box(Diamond(p))) => Diamond(p) & Diamond(Not(Diamond(p)))
    ("Axioma 5 - Euclidiano (Violación)", ast.And(ast.Diamond(p), ast.Diamond(ast.Box(ast.Not(p)))), "UNSAT"),

    # Dualidades Modales
    ("Dualidad Modal 1", ast.And(ast.Not(ast.Box(p)), ast.Box(p)), "UNSAT"),
    ("Dualidad Modal 2", ast.And(ast.Not(ast.Diamond(p)), ast.Diamond(p)), "UNSAT"),

    # --- 3. CONFLICTO DE DIAMANTES Y RETOS DE DCC ---
    ("Caja vs Diamante Incompatible", ast.And(ast.Box(p), ast.Diamond(ast.Not(p))), "UNSAT"),
    ("Diamantes Independientes (Requiere W>=2)", ast.And(ast.Diamond(p), ast.Diamond(ast.Not(p))), "SAT"),
    ("Diamantes Compatibles Compartidos", ast.And(ast.Diamond(ast.And(p, q)), ast.Diamond(ast.And(p, r))), "SAT"),
    ("Diamante con Contradicción Interna", ast.Diamond(ast.And(p, ast.Not(p))), "UNSAT"),
    ("Cajas Contradictorias", ast.And(ast.Box(p), ast.Box(ast.Not(p))), "UNSAT"),

    # --- 4. TRAMPAS DE PROFUNDIDAD MODAL ANIDADA (d >= 2) ---
    ("Reducción de Profundidad S5 - Positiva", ast.And(ast.Box(ast.Diamond(ast.Box(p))), ast.Diamond(ast.Not(p))), "UNSAT"),
    ("Reducción de Profundidad S5 - Satisfacible", ast.And(ast.Box(ast.Diamond(p)), ast.Diamond(ast.Not(p))), "SAT"),
    ("Interacción Crítica Cruzada", ast.And(ast.Diamond(ast.And(p, ast.Box(q))), ast.Diamond(ast.And(p, ast.Diamond(ast.Not(q))))), "UNSAT"),
    ("Anidación Compleja SAT", ast.And(ast.Diamond(ast.And(p, ast.Box(ast.Or(q, ast.Diamond(r))))), ast.Diamond(ast.Not(q))), "SAT"),
]


def run_test_suite():
    print("=" * 75)
    print(" 🚀 INICIANDO SUITE DE PRUEBAS EXTREMA PARA KhSAT Y S5ModelChecker")
    print("=" * 75)

    passed = 0
    failed = 0

    for idx, (name, formula_ast, expected) in enumerate(TEST_CASES, 1):
        print(f"[{idx:02d}/{len(TEST_CASES):02d}] {name:<45} ... ", end="")
        try:
            verdict, verified, worlds_used = solve_formula_internal(formula_ast)

            if verdict == expected:
                if verdict == "SAT" and not verified:
                    print("❌ FALLÓ (Model Checker rechazó el modelo SAT)")
                    failed += 1
                else:
                    print(f"✅ PASÓ [{verdict}] (W={worlds_used})")
                    passed += 1
            else:
                print(f"❌ FALLÓ (Obtenido: {verdict}, Esperado: {expected})")
                failed += 1
        except Exception as e:
            print(f"💥 EXCEPCIÓN: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 75)
    print(" 🧪 EJECUTANDO PRUEBAS UNITARIAS DE INYECCIÓN DE FALLOS EN S5ModelChecker")
    print("=" * 75)

    mc_passed = 0
    mc_failed = 0

    # Test MC-1: Inyección de Mundo Raíz Inexistente
    print("[MC-1] Rechazo de root_world inválido (99) ........ ", end="")
    try:
        S5ModelChecker(worlds=[1, 2], valuation={("p", 1): True}, root_world=99)
        print("❌ FALLÓ (No lanzó ValueError)")
        mc_failed += 1
    except ValueError:
        print("✅ PASÓ (Lanzó ValueError correctamente)")
        mc_passed += 1

    # Test MC-2: Asignación a Mundo Inexistente en Valuación
    print("[MC-2] Rechazo de mundo huérfano en valuación ..... ", end="")
    try:
        S5ModelChecker(worlds=[1, 2], valuation={("p", 5): True}, root_world=1)
        print("❌ FALLÓ (No lanzó ValueError)")
        mc_failed += 1
    except ValueError:
        print("✅ PASÓ (Lanzó ValueError correctamente)")
        mc_passed += 1

    # Test MC-3: Detección de Mutación / Corrupción de Modelo (Sabotaje)
    print("[MC-3] Detección de modelo corrupto (Box Violado) . ", end="")
    ast_box_p = ast.Box(ast.Var("p"))
    corrupted_val = {("p", 1): True, ("p", 2): False}
    checker_corrupted = S5ModelChecker(worlds=[1, 2], valuation=corrupted_val, root_world=1)
    if not checker_corrupted.verify(ast_box_p):
        print("✅ PASÓ (Detectó la corrupción y devolvió False)")
        mc_passed += 1
    else:
        print("❌ FALLÓ (Aprobó un modelo inválido - Falso Positivo)")
        mc_failed += 1

    print("\n" + "=" * 75)
    print(f" RESUMEN FINAL:")
    print(f"  • Pruebas de Pipeline y Semántica S5 : {passed}/{len(TEST_CASES)} Pasadas")
    print(f"  • Pruebas de Robustez Model Checker : {mc_passed}/{mc_passed + mc_failed} Pasadas")
    print("=" * 75)


if __name__ == "__main__":
    run_test_suite()