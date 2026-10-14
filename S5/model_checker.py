"""
S5 Kripke Model Checker (Strict Semantic Version).
Verifies whether an explicit Kripke Model M = <W, R, V> satisfies an S5 AST formula.
In S5 logic, the accessibility relation R is universal over W (R = W x W).
"""

import S5.AST_S5 as ast


class S5ModelChecker:
    def __init__(self, worlds, valuation, root_world=None):
        """
        :param worlds: Iterable, explicit set or list of valid world identifiers (e.g., [1, 2, 3] or {10, 20}).
        :param valuation: Dict[(var_name, world_id), bool], truth assignment.
        :param root_world: World identifier where the formula is verified (defaults to first in worlds).
        """
        if not worlds:
            raise ValueError("El conjunto de mundos W no puede estar vacío.")

        self.W = sorted(list(set(worlds)))

        # 1. Asignar y validar el mundo raíz
        self.root_world = self.W[0] if root_world is None else root_world
        if self.root_world not in self.W:
            raise ValueError(
                f"El mundo raíz designado ({self.root_world}) no pertenece al conjunto de mundos W={self.W}."
            )

        # 2. Validar que la valuación no contenga referencias a mundos fuera de W
        invalid_worlds = {w for (_, w) in valuation.keys() if w not in self.W}
        if invalid_worlds:
            raise ValueError(
                f"La valuación contiene asignaciones para mundos inexistentes en W: {invalid_worlds}"
            )

        self.V = valuation

    def evaluate(self, node, w):
        """Evaluación recursiva directa bajo semántica de Kripke."""
        if w not in self.W:
            raise ValueError(f"Intento de evaluar en un mundo inexistente: {w}")

        if isinstance(node, ast.Var):
            # Convención de Mundo Cerrado (CWA)
            return self.V.get((node.name, w), False)

        elif isinstance(node, ast.Not):
            return not self.evaluate(node.operand, w)

        elif isinstance(node, ast.And):
            return self.evaluate(node.left, w) and self.evaluate(node.right, w)

        elif isinstance(node, ast.Or):
            return self.evaluate(node.left, w) or self.evaluate(node.right, w)

        elif isinstance(node, ast.Box):
            # Semántica S5: Accesibilidad universal sobre W
            return all(self.evaluate(node.operand, wp) for wp in self.W)

        elif isinstance(node, ast.Diamond):
            # Semántica S5: Accesibilidad universal sobre W
            return any(self.evaluate(node.operand, wp) for wp in self.W)

        elif isinstance(node, ast.Top):
            return True

        elif isinstance(node, ast.Bot):
            return False

        # Verificación por nombre de clase para nodos no reducidos
        node_type = node.__class__.__name__
        if node_type in ("Imp", "Implies"):
            return (not self.evaluate(node.left, w)) or self.evaluate(node.right, w)
        elif node_type in ("Equiv", "Iff"):
            return self.evaluate(node.left, w) == self.evaluate(node.right, w)

        raise TypeError(f"Tipo de nodo AST no reconocido: {type(node)} ({node_type})")

    def verify(self, formula_ast):
        """Verifica la fórmula en el mundo raíz del modelo."""
        return self.evaluate(formula_ast, self.root_world)