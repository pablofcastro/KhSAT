import subprocess
import os
import csv
import argparse
import re
import sys
from pathlib import Path

def run_solver(instance_path, method):
    try:
        output_bytes = subprocess.run(
            [sys.executable, "../../kh_solver.py", "-f", instance_path, "-m", method], 
            timeout=300, 
            capture_output=True
        ).stdout
        output = output_bytes.decode('utf-8', errors='ignore')
        
        time_val = "300"
        result_val = "ERR"
        
        for line in output.splitlines():
            if line.startswith("Time"):
                time_val = line.split()[1]
            elif line.startswith("The formula"):
                result_val = line.split()[3].replace(".", "")
            elif line.strip() in ["SAT", "UNSAT"]:
                result_val = line.strip()
                
        return result_val, time_val
    except subprocess.TimeoutExpired:
        return "TO", "300"
    except Exception as e:
        print(f"Error running {instance_path} with method {method}: {e}")
        return "ERR", "300"

#acá cambiar la carpeta de las formulas
def process_batch(i, formulas_dir="../cnf_formulas/", method="incremental"):
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+).kh$")
    files = []
    
    if not os.path.exists(formulas_dir):
        print(f"Directory not found: {formulas_dir}")
        return
        
    for filename in os.listdir(formulas_dir):
        m = pattern.match(filename)
        if m:
            n = int(m.group(1))
            if n < i*10 and n >= (i-1)*10:
                files.append(filename)
                
    result = []
    total_files = len(files)
    if total_files == 0:
        print(f"No files found for batch {i} in directory {formulas_dir}")
        return
        
    print(f"Running batch {i} ({total_files} files) using method: '{method}'")
    processed = 0
    
    for file in files:
        row = {}
        m = pattern.match(file)
        if m:
            row["form"] = f"formula{m.group(1)}"
            row["pos"] = m.group(2)
            row["neg"] = m.group(3)
        
        instance_path = os.path.join(formulas_dir, file)
        
        # Ejecución del método único seleccionado
        res_val, time_str = run_solver(instance_path, method)
        
        row["method"] = method
        row["time"] = time_str
        row["result"] = res_val
        
        processed += 1
        print(f"Progress: {round((processed/total_files) * 100, 1)}% ({file} -> {res_val} in {time_str}s)")
        result.append(row)
        
    if not result:
        return
        
    fieldnames = result[0].keys()
    
    # Crear carpeta de salida si no existe
    graphs_dir = Path("graphs")
    graphs_dir.mkdir(parents=True, exist_ok=True)
    
    # Nombre de archivo dinámico según lote y método
    method_clean = method.replace("-", "_")
    csv_file = graphs_dir / f"cnf_formulas_batch_{i}_{method_clean}.csv" #aca cambiar el nombre de .csv
    
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result)
        
    print(f"\n[OK] CSV file generated: {csv_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process formulas in batches using a single solver method.")
    parser.add_argument(
        "--dir",
        type=str,
        default="../cnf_formulas/", #cambiar
        help="Path to the directory containing formulas (default: ../formulas/)"
    )
    parser.add_argument("--batch", type=int, default=1, help="The batch to be processed (default: 1)")
    parser.add_argument(
        "-m", "--method",
        type=str,
        choices=["incremental", "basic-opt"],
        default="incremental",
        help="Solver method to execute: 'incremental' or 'basic-opt' (default: incremental)"
    )
    parser.add_argument("--all", action='store_true', help="Option to process all batches (1 to 5)")
    
    args = parser.parse_args()
    
    batches = [1, 2, 3, 4, 5] if args.all else [args.batch]
    
    for b in batches:
        print(f"\n================ Processing Batch {b} ================")
        process_batch(b, args.dir, args.method)