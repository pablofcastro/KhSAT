import subprocess
import os
import sys
import csv
import argparse
import re
import statistics
import concurrent.futures

ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(ruta_raiz)

# Dependencias de S5 para el análisis profundo de la topología modal
import S5.parser_s5 as s5parser
import S5.NNFVisitor as tonnf
import S5.DiamondVisitor as diamond_counter
import S5.AST_S5 as ast_s5

# Aumentamos drásticamente el límite de recursión para no crashear con el AST gigante
sys.setrecursionlimit(10000)

def count_operators(node):
    """Recorre el AST original recursivamente y cuenta exactamente (Cajas, Diamantes)"""
    if isinstance(node, ast_s5.Var) or isinstance(node, (ast_s5.Top, ast_s5.Bot)):
        return 0, 0
    elif isinstance(node, ast_s5.Not):
        return count_operators(node.operand)
    elif isinstance(node, ast_s5.Box):
        b, d = count_operators(node.operand)
        return b + 1, d
    elif isinstance(node, ast_s5.Diamond):
        b, d = count_operators(node.operand)
        return b, d + 1
    elif isinstance(node, (ast_s5.And, ast_s5.Or)):
        b1, d1 = count_operators(node.left)
        b2, d2 = count_operators(node.right)
        return b1 + b2, d1 + d2
    return 0, 0

def analyze_formula(file_path):
    """Parsea la fórmula, extrae los mundos asfixiados por Tsetin y cuenta los operadores reales."""
    try:
        with open(file_path, 'r') as f:
            formula_str = f.read()
            
        parsed = s5parser.parse(formula_str)
        # Contamos A y E tal cual salieron del generador
        boxes, diamonds = count_operators(parsed)
        
        # Calculamos los mundos
        nnf_form = parsed.accept(tonnf.ToNNF())
        mundos = nnf_form.accept(diamond_counter.DiamondVisitor()) + 1
        
        return mundos, boxes, diamonds
    except Exception as e:
        print(f"Error analizando la topología de {file_path}: {e}")
        return -1, -1, -1

def process_single_file(file, runs):
    """Procesa una sola fórmula. Es enviada a un núcleo de la CPU por el orquestador."""
    row = {}
    instance = file.replace(".s5","").split('-')
    row["form"] = instance[0]
    row["n"] = instance[1] 
    row["m"] = instance[2] 
    row["ratio"] = round(int(instance[2])/int(instance[1]), 2) 
    row["p"] = instance[4] 
    row["pd"] = instance[5] # EL NUEVO PARÁMETRO DE PROPORCIÓN CAJA/DIAMANTE
    
    instance_path = os.path.join("../formulasS5/", file)
    
    # Análisis estructural
    mundos, boxes, diamonds = analyze_formula(instance_path)
    row["worlds"] = mundos
    row["boxes"] = boxes
    row["diamonds"] = diamonds
    # Si no hay diamantes, la división por cero rompería, dejamos las cajas como valor absoluto
    row["modal_ratio"] = round(boxes / diamonds, 3) if diamonds > 0 else boxes
    
    times = []
    results = []
    timed_out = False
    
    for r in range(runs) :
        try :
            # Ejecutamos Z3 (asegúrate de que s5_solver.py también tenga sys.setrecursionlimit(10000))
            output = subprocess.run([sys.executable, "../../s5_solver.py", "-f", instance_path], timeout=900, capture_output=True).stdout.decode()
            lines = output.splitlines()
            for line in lines :
                if "Time:" in line :
                    times.append(float(line.split()[1]))
                elif "SAT" in line or "UNSAT" in line or "unsat" in line :
                    results.append("SAT" if "SAT" in line else "UNSAT")
        except subprocess.TimeoutExpired:
             print(f"Timeout (900s) en la corrida {r+1} de {file}")
             timed_out = True
        except Exception as e:
            print(f'Error (Crasheo) ejecutando {file}: {e}')
            timed_out = True
            
    row["time"] = str(statistics.median(times)) if times else "900" 
    row["result"] = results[0] if results else ("TO" if timed_out else "TO")
    row["size"] = os.path.getsize(instance_path)
    
    return row

def process_batch(batch_num, runs) :
    # Regex actualizado con un bloque extra para capturar "pd"
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+)-(\d+)-([\d.]+)-([\d.]+).s5$")
    files_to_process = []
    
    csv_filename = f"output-batch{batch_num}.csv"
    processed_formulas = set()
    
    # 1. SISTEMA DE REANUDACIÓN: Verificamos qué fórmulas ya están resueltas
    if os.path.exists(csv_filename):
        with open(csv_filename, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader, None) # Saltar el encabezado
            for row in reader:
                 if row: 
                     # Creamos una huella digital única: form - n - m - p - pd
                     formula_key = f"{row[0]}-{row[1]}-{row[2]}-{row[4]}-{row[5]}"
                     processed_formulas.add(formula_key)
        print(f"Encontradas {len(processed_formulas)} fórmulas ya procesadas en {csv_filename}. Serán omitidas.")

    # 2. FILTRAMOS LO QUE FALTA HACER
    for filename in os.listdir("../formulasS5/"):
        m = pattern.match(filename)
        if m:
            inst_id = int(m.group(1))
            if inst_id < batch_num*10 and inst_id >= (batch_num-1)*10 :
                parts = filename.replace(".s5","").split('-')
                # La huella digital del archivo: form - n - m - p - pd
                formula_key = f"{parts[0]}-{parts[1]}-{parts[2]}-{parts[4]}-{parts[5]}"
                
                if formula_key not in processed_formulas:
                     files_to_process.append(filename)
                
    total_files_batch = len(files_to_process)
    if total_files_batch == 0:
        print(f"El Batch {batch_num} ya está 100% completo. No hay nada nuevo que procesar.")
        return

    cores = os.cpu_count()
    print(f"Batch {batch_num}: Procesando {total_files_batch} fórmulas faltantes en PARALELO ({cores} hilos)...")
    
    # Todas las columnas, incluyendo pd y la topología modal
    fieldnames = ["form", "n", "m", "ratio", "p", "pd", "worlds", "boxes", "diamonds", "modal_ratio", "time", "result", "size"]
    
    # 3. EJECUCIÓN PARALELA CON ESCRITURA EN DISCO EN TIEMPO REAL
    write_header = not os.path.exists(csv_filename) or os.path.getsize(csv_filename) == 0

    with open(csv_filename, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
            
        processed_count = 0
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=cores) as executor:
            futures = {executor.submit(process_single_file, f, runs): f for f in files_to_process}
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    row_data = future.result()
                    writer.writerow(row_data)
                    # Forzamos el guardado en el disco físico. Esto es lo que nos salva ante un Ctrl+C.
                    csvfile.flush() 
                except Exception as exc:
                    print(f"Una fórmula generó una excepción: {exc}")
                    
                processed_count += 1
                if processed_count % 10 == 0 or processed_count == total_files_batch:
                    print(f"Progreso Batch {batch_num}: {round((processed_count/total_files_batch) * 100, 1)}% ({processed_count}/{total_files_batch})")

if __name__ == "__main__" :
    parser = argparse.ArgumentParser(description="Process the formulas in batches.")
    parser.add_argument("--batch", type=int, default=3, help="The batch to be processed")
    parser.add_argument("--all", action="store_true", default=False, help="Option to process all the batches")
    parser.add_argument("--runs", type=int, default=3, help="Number of solver executions per formula")
    
    args = parser.parse_args()
    
    if not args.all :
        print(f"Procesando batch: {args.batch}")
        process_batch(args.batch, args.runs)
        print(f"Resultado finalizado en output-batch{args.batch}.csv")
    else :
        for i in [1,2,3,4,5] :
            print(f"--- Iniciando Batch {i} ---")
            process_batch(i, args.runs)