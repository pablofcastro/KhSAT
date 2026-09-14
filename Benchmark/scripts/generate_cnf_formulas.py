import os
import random

# Definir directorios del proyecto
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
output_dir = os.path.join(project_root, 'cnf_formulas')

# Crear la carpeta de salida si no existe
os.makedirs(output_dir, exist_ok=True)

# Lista de proposiciones disponibles (p0 a p9)
PROPOSITIONS = [f"p{i}" for i in range(10)]

def generate_clause():
    """Selecciona 3 proposiciones aleatorias sin repetición y las une con '|'."""
    chosen = random.sample(PROPOSITIONS, 3)
    return f"({chosen[0]} | {chosen[1]} | {chosen[2]})"

def generate_cnf():
    """Genera una fórmula en CNF con 2 o 3 cláusulas conectadas con '&'."""
    num_clauses = random.choice([2, 3])
    clauses = [generate_clause() for _ in range(num_clauses)]
    return " & ".join(clauses)

def generate_pos_atom():
    """Genera un átomo positivo Kh(pre, post) donde pre y post son CNFs."""
    pre = generate_cnf()
    post = generate_cnf()
    return f"Kh({pre},{post})"

def generate_neg_atom():
    """Genera el átomo negativo ~Kh(pi, pj) con 2 proposiciones distintas."""
    pi, pj = random.sample(PROPOSITIONS, 2)
    return f"~Kh({pi},{pj})"

def create_complex_formula(num_positives):
    # Nombre del archivo actualizado con el formato solicitado
    formula_name = f"formula{num_positives + 1}-{num_positives}-1.kh"
    file_path = os.path.join(output_dir, formula_name)

    # 1. Generar los átomos positivos
    positives = [generate_pos_atom() for _ in range(num_positives)]

    # 2. Generar el único átomo negativo
    negative = generate_neg_atom()

    # 3. Concatenar todo separado por ';'
    full_formula = ";".join(positives) + ";" + negative

    # 4. Guardar archivo
    with open(file_path, "w") as f:
        f.write(full_formula)

if __name__ == "__main__":
    # Genera fórmulas con 1 hasta 49 átomos positivos
    for num_pos in range(1, 50):
        create_complex_formula(num_pos)