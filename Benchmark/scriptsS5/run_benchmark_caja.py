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

import S5.parser_s5 as s5parser
import S5.NNFVisitor as tonnf
import S5.DiamondVisitor as diamond_counter
import S5.AST_S5 as ast_s5

sys.setrecursionlimit(10000)

def count_operators(node):
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
    try:
        with open(file_path, 'r') as f:
            formula_str = f.read()
            
        parsed = s5parser.parse(formula_str)
        boxes, diamonds = count_operators(parsed)
        
        nnf_form = parsed.accept(tonnf.ToNNF())
        mundos = nnf_form.accept(diamond_counter.DiamondVisitor()) + 1
        
        return mundos, boxes, diamonds
    except Exception as e:
        print(f"Error analizando {file_path}: {e}")
        return -1, -1, -1

def process_single_file(file, runs):
    row = {}
    instance = file.replace(".s5","").split('-')
    row["form"] = instance[0].replace("formula", "")
    row["n"] = int(instance[1])
    row["m"] = int(instance[2])
    row["l"] = int(instance[3])
    row["ratio"] = round(row["m"] / row["n"], 2)
    row["D_target"] = int(instance[4])
    row["B_target"] = int(instance[5]) 
    
    instance_path = os.path.join("../formulasS5/", file)
    
    mundos, boxes, diamonds = analyze_formula(instance_path)
    row["worlds"] = mundos
    row["boxes"] = boxes
    row["diamonds"] = diamonds
    row["modal_ratio"] = round(diamonds / boxes, 3) if boxes > 0 else 999.9 # Diam/Cajas
    
    times = []
    results = []
    timed_out = False
    
    for r in range(runs):
        try :
            output = subprocess.run([sys.executable, "../../s5_solver.py", "-f", instance_path], timeout=900, capture_output=True).stdout.decode()
            for line in output.splitlines():
                if "Time:" in line :
                    times.append(float(line.split()[1]))
                elif "SAT" in line or "UNSAT" in line or "unsat" in line :
                    results.append("SAT" if "SAT" in line else "UNSAT")
        except subprocess.TimeoutExpired:
             timed_out = True
        except Exception:
            timed_out = True
            
    row["time"] = str(round(statistics.median(times), 4)) if times else "900" 
    row["result"] = results[0] if results else ("TO" if timed_out else "ERR")
    row["size"] = os.path.getsize(instance_path)
    
    return row

def process_batch(batch_num, runs):
    # REGEX para el nuevo formato: formula{i}-{n}-{m}-{l}-{D}-{B}.s5
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)\.s5$")
    files_to_process = []
    
    csv_filename = f"output-batch{batch_num}.csv"
    processed_formulas = set()
    
    # LECTURA ROBUSTA DEL CSV PARA REANUDAR
    if os.path.exists(csv_filename):
        with open(csv_filename, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                 # Huella dactilar exacta: id-n-m-l-D-B
                 formula_key = f"{row['form']}-{row['n']}-{row['m']}-{row['l']}-{row['D_target']}-{row['B_target']}"
                 processed_formulas.add(formula_key)
                 
        print(f"Batch {batch_num}: Encontradas {len(processed_formulas)} fórmulas ya resueltas. Serán omitidas.")

    for filename in os.listdir("../formulasS5/"):
        m = pattern.match(filename)
        if m:
            inst_id = int(m.group(1))
            # Distribuimos en batches según el ID de instancia (1-10)
            if inst_id == batch_num:
                parts = filename.replace(".s5","").split('-')
                formula_key = f"{parts[0].replace('formula', '')}-{parts[1]}-{parts[2]}-{parts[3]}-{parts[4]}-{parts[5]}"
                
                if formula_key not in processed_formulas:
                     files_to_process.append(filename)
                
    total_files_batch = len(files_to_process)
    if total_files_batch == 0:
        return

    cores = max(1, os.cpu_count() - 1) # Dejamos 1 hilo libre para que no se congele la PC
    print(f"Batch {batch_num}: Procesando {total_files_batch} fórmulas en {cores} hilos...")
    
    fieldnames = ["form", "n", "m", "l", "ratio", "D_target", "B_target", "worlds", "boxes", "diamonds", "modal_ratio", "time", "result", "size"]
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
                    writer.writerow(future.result())
                    csvfile.flush() 
                except Exception as exc:
                    print(f"Excepción: {exc}")
                
                processed_count += 1
                if processed_count % 5 == 0 or processed_count == total_files_batch:
                    print(f"Progreso Batch {batch_num}: {round((processed_count/total_files_batch)*100, 1)}%")

if __name__ == "__main__" :
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--all", action="store_true", default=False)
    parser.add_argument("--runs", type=int, default=1) # Bajado a 1 corrida por defecto para ir más rápido
    args = parser.parse_args()
    
    if not args.all:
        process_batch(args.batch, args.runs)
    else:
        # Hacemos 10 batches (uno por cada instancia 1 al 10)
        for i in range(1, 11): 
            process_batch(i, args.runs)