"""
S5 Kripke Model Checker.
Verifies whether a Kripke Model M = <W, V> satisfies an S5 AST formula.
In S5 logic, the accessibility relation R is universal (R = W x W).
"""

import S5.AST_S5 as ast


class S5ModelChecker:
    def __init__(self, worlds_count, valuation, root_world=None):
        # 1. Extraer todos los IDs de mundos presentes en la valuación de Z3
        extracted_worlds = {w for (_, w) in valuation.keys()}

        # 2. Si hay mundos en la valuación, usarlos; de lo contrario, usar indexación 1-based
        if extracted_worlds:
            self.W = sorted(list(extracted_worlds))
        else:
            self.W = list(range(1, worlds_count + 1))

        # 3. Asignar el mundo raíz al primer mundo disponible (por defecto min(W) o 1)
        if root_world is None:
            self.root_world = self.W[0] if self.W else 1
        else:
            self.root_world = root_world

        self.V = valuation

    def evaluate(self, node, w):
        if isinstance(node, ast.Var):
            return self.V.get((node.name, w), False)

        elif isinstance(node, ast.Not):
            return not self.evaluate(node.operand, w)

        elif isinstance(node, ast.And):
            return self.evaluate(node.left, w) and self.evaluate(node.right, w)

        elif isinstance(node, ast.Or):
            return self.evaluate(node.left, w) or self.evaluate(node.right, w)

        elif isinstance(node, ast.Box):
            return all(self.evaluate(node.operand, w_prime) for w_prime in self.W)

        elif isinstance(node, ast.Diamond):
            return any(self.evaluate(node.operand, w_prime) for w_prime in self.W)

        elif isinstance(node, ast.Top):
            return True

        elif isinstance(node, ast.Bot):
            return False

        # Verificación por nombre de clase por si se evalúan nodos de implicación
        node_type = node.__class__.__name__
        if node_type in ("Imp", "Implies"):
            return (not self.evaluate(node.left, w)) or self.evaluate(node.right, w)
        elif node_type in ("Equiv", "Iff"):
            return self.evaluate(node.left, w) == self.evaluate(node.right, w)

        raise TypeError(f"Unknown AST node type: {type(node)} ({node_type})")

    def verify(self, formula_ast):
        return self.evaluate(formula_ast, self.root_world)