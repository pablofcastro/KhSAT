import os
import csv
import subprocess
import sys
import time
import re
from pathlib import Path

# Garantiza la ruta absoluta bBenchmark/scripts/graphs
SCRIPT_DIR = Path(__file__).resolve().parent
GRAPHS_DIR = SCRIPT_DIR / "graphs"

def sort_key_formula(filename):
    numbers = re.findall(r'\d+', filename)
    if numbers:
        return [int(num) for num in numbers]
    return [filename]

def run_solver(instance_path, method="incremental"):
    try:
        start_time = time.time()
        # Ruta a kh_solver.py (KhSAT/kh_solver.py)
        solver_path = SCRIPT_DIR.parent.parent / "kh_solver.py"
        
        process = subprocess.run(
            [sys.executable, str(solver_path), "-f", str(instance_path), "-m", method],
            timeout=300,
            capture_output=True
        )
        elapsed_time = time.time() - start_time
        output = process.stdout.decode('utf-8', errors='ignore')
        error_output = process.stderr.decode('utf-8', errors='ignore')
        
        result_val = "ERR"
        for line in output.splitlines():
            if line.startswith("The formula"):
                result_val = line.split()[3].replace(".", "")
            elif line.strip() in ["SAT", "UNSAT"]:
                result_val = line.strip()
                
        if result_val == "ERR" and error_output.strip():
            print(f"  [STDERR]: {error_output.strip()}")

        return result_val, f"{elapsed_time:.4f}"
    
    except subprocess.TimeoutExpired:
        return "TO", "300.0000"
    except Exception as e:
        print(f"  [EXCEPTION]: {e}")
        return "ERR", "300.0000"

def run_all_tree_incremental(formulas_dir_name="formulas"):
    # Apunta a bBenchmark/<formulas_dir_name>
    benchmark_dir = SCRIPT_DIR.parent
    formulas_dir = benchmark_dir / formulas_dir_name
    
    # Asegurar existencia de scripts/graphs
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    output_csv = GRAPHS_DIR / "all_tree_formulas_incremental.csv"
    
    if not formulas_dir.exists():
        print(f"Directory not found: {formulas_dir}")
        return

    pattern = re.compile(r"formula(\d+)_(\d+)_(\d+)_leaf_\d+\.kh$")
    files = []
    
    # Buscar y filtrar los archivos de tipo árbol
    for filename in os.listdir(formulas_dir):
        if pattern.match(filename) or filename.endswith('.csv'):
            files.append(filename)
            
    files.sort(key=sort_key_formula)
    total_files = len(files)
    
    if total_files == 0:
        print(f"No formula files found in {formulas_dir}")
        return

    print(f"Processing {total_files} tree formulas with 'incremental' mode...")
    
    results = []
    for idx, file in enumerate(files, 1):
        instance_path = formulas_dir / file
        print(f"[{idx}/{total_files}] Running: {file}")
        
        row = {"formula_name": file}
        m = pattern.match(file)
        if m:
            row["form"] = f"formula{m.group(1)}"
            row["pos"] = m.group(2)
            row["neg"] = m.group(3)
        else:
            row["form"] = file
            row["pos"] = "N/A"
            row["neg"] = "N/A"
        
        result, exec_time = run_solver(instance_path, method="incremental")
        
        row["result"] = result
        row["time_seconds"] = exec_time
        row["mode"] = "incremental"
        
        results.append(row)

    fieldnames = ["formula_name", "form", "pos", "neg", "result", "time_seconds", "mode"]
    
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nExecution finished! Results saved to:\n{output_csv}")

if __name__ == "__main__":
    # Puedes cambiar "formulas" por el nombre exacto de la carpeta si se llama diferente (ej: "tree_formulas")
    run_all_tree_incremental(formulas_dir_name="formulas_tree")