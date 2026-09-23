import random

def phi(n, m, l, D, B, W):
    """
    Generador S5 con Control Topológico Exacto.
    D = Diamantes exactos
    B = Cajas exactas
    W = Mundos exactos
    """
    target_d_clauses = W - 1 # Cláusulas que DEBEN tener al menos un diamante
    
    # --- Controles de Física Matemática ---
    if target_d_clauses > D:
        raise ValueError(f"Faltan diamantes: Para {W} mundos necesitas mínimo {target_d_clauses} diamantes.")
    if target_d_clauses > m:
        raise ValueError(f"Faltan cláusulas: Para {W} mundos necesitas mínimo {target_d_clauses} cláusulas.")
    if (D + B) > (m * l):
        raise ValueError("Falta espacio: Tienes más operadores que literales totales.")

    # 1. Crear matriz de operadores (m cláusulas x l huecos vacíos)
    ops_matrix = [["" for _ in range(l)] for _ in range(m)]
    
    # 2. Elegir cuáles cláusulas serán las "Creadoras de Mundos"
    d_clause_indices = random.sample(range(m), target_d_clauses)
    
    # 3. Garantizar al menos 1 Diamante (E) en cada cláusula creadora
    for idx in d_clause_indices:
        pos = random.randint(0, l - 1)
        ops_matrix[idx][pos] = "E"
        
    # 4. Repartir los Diamantes (E) sobrantes SOLO en las cláusulas creadoras
    # (Para no crear mundos accidentales en otras cláusulas)
    remaining_E = D - target_d_clauses
    available_E_spots = [(i, j) for i in d_clause_indices for j in range(l) if ops_matrix[i][j] == ""]
    
    if remaining_E > len(available_E_spots):
        raise ValueError("Las cláusulas creadoras están llenas, no caben los diamantes sobrantes.")
        
    chosen_E_spots = random.sample(available_E_spots, remaining_E)
    for i, j in chosen_E_spots:
        ops_matrix[i][j] = "E"
        
    # 5. Repartir las Cajas (A) en cualquier hueco sobrante de CUALQUIER cláusula
    available_A_spots = [(i, j) for i in range(m) for j in range(l) if ops_matrix[i][j] == ""]
    if B > len(available_A_spots):
         raise ValueError("No hay suficiente espacio para las Cajas (A).")
         
    chosen_A_spots = random.sample(available_A_spots, B)
    for i, j in chosen_A_spots:
        ops_matrix[i][j] = "A"

    # 6. Construir la fórmula S5 real
    clauses_str = []
    for i in range(m):
        clause_lits = []
        for j in range(l):
            var = f"p{random.randint(0, n-1)}"
            if random.random() < 0.5:
                var = f"~{var}" # Negación
            
            op = ops_matrix[i][j]
            if op != "":
                clause_lits.append(f"{op} {var}")
            else:
                clause_lits.append(var)
        
        clauses_str.append("(" + " | ".join(clause_lits) + ")")
        
    return " & ".join(clauses_str)