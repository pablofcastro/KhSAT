import random

def phi(n, m, l, D, B):
    """
    Generador de fórmulas S5 con Cardinalidad Exacta.
    D = Cantidad EXACTA de Diamantes
    B = Cantidad EXACTA de Cajas
    """
    total_literals = m * l
    P = total_literals - D - B # Literales puramente proposicionales
    
    if P < 0:
        raise ValueError(f"Físicamente imposible: {D}E + {B}A = {D+B} modales, pero la fórmula solo tiene {total_literals} literales.")

    # 1. Creamos la "bolsa" exacta de operadores y la mezclamos
    operators = ["E"] * D + ["A"] * B + [""] * P
    random.shuffle(operators)
    
    # 2. Construimos la fórmula sacando operadores de la bolsa
    clauses = []
    for _ in range(m):
        clause_lits = []
        for _ in range(l):
            var = f"p{random.randint(0, n-1)}"
            
            # Negación aleatoria proposicional (50%)
            if random.random() < 0.5:
                var = f"~{var}"
                
            # Asignamos operador
            op = operators.pop()
            if op:
                clause_lits.append(f"{op} {var}")
            else:
                clause_lits.append(var)
                
        clauses.append("(" + " | ".join(clause_lits) + ")")
        
    return " & ".join(clauses)