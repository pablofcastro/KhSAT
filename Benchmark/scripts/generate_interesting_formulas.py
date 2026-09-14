import os
import random

# Definir la ruta base del script y la carpeta de salida 'interesting_formulas_shuffled'
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
path_interesting_formulas_shuffled = os.path.join(project_root, 'interesting_formulas')

# Crear la carpeta de destino si no existe
os.makedirs(path_interesting_formulas_shuffled, exist_ok=True)

# Átomo positivo
def kh_pos(i):
    return f"Kh(p{i},p{i+1})"

# Átomo negativo
def kh_neg(m):
    return f"~Kh(p0,p{m})"

def create_interesting_formulas_shuffled(m):
    formula_name = f"formula{m+1}-{m}-1.kh"
    file_path = os.path.join(path_interesting_formulas_shuffled, formula_name)

    # 1. Generar la lista de átomos positivos
    positives = [kh_pos(i) for i in range(m)]

    # 2. Mezclar la lista de átomos positivos aleatoriamente
    #random.shuffle(positives)

    # 3. Concatenar los átomos positivos desordenados con ';'
    # 4. Agregar la fórmula negativa al final
    if positives:
        interesting_formula = ";".join(positives) + ";" + kh_neg(m)
    else:
        interesting_formula = kh_neg(m)

    # Guardar en el archivo correspondiente
    with open(file_path, "w") as f:
        f.write(interesting_formula)

if __name__ == "__main__":
    for m in range(1, 50):  
        create_interesting_formulas_shuffled(m)