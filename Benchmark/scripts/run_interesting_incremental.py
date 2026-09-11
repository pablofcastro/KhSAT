import os
import csv
import subprocess
import sys
import time
import re

def sort_key_formula(filename):
    numbers = re.findall(r'\d+', filename)
    if numbers:
        return [int(num) for num in numbers]
    return [filename]

def run_solver(instance_path, method="incremental"):
    try:
        start_time = time.time()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Path to kh_solver.py (KhSAT/kh_solver.py)
        solver_path = os.path.abspath(os.path.join(script_dir, "..", "..", "kh_solver.py"))
        
        process = subprocess.run(
            [sys.executable, solver_path, "-f", instance_path, "-m", method],
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

def run_all_interesting_incremental():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    benchmark_dir = os.path.abspath(os.path.join(script_dir, ".."))
    
    formulas_dir = os.path.join(benchmark_dir, "interesting_formulas")
    graphs_dir = os.path.join(script_dir, "graphs")
    os.makedirs(graphs_dir, exist_ok=True)
    
    output_csv = os.path.join(graphs_dir, "all_interesting_formulas_incremental.csv")
    
    if not os.path.exists(formulas_dir):
        print(f"Directory not found: {formulas_dir}")
        return

    files = [f for f in os.listdir(formulas_dir) if os.path.isfile(os.path.join(formulas_dir, f))]
    
    # Ordenar numéricamente las fórmulas
    files.sort(key=sort_key_formula)
    
    total_files = len(files)
    
    if total_files == 0:
        print(f"No formula files found in {formulas_dir}")
        return

    print(f"Processing {total_files} interesting formulas with 'incremental' mode...")
    
    results = []
    for idx, file in enumerate(files, 1):
        instance_path = os.path.join(formulas_dir, file)
        print(f"[{idx}/{total_files}] Running: {file}")
        
        result, exec_time = run_solver(instance_path, method="incremental")
        
        results.append({
            "formula_name": file,
            "result": result,
            "time_seconds": exec_time,
            "mode": "incremental"
        })

    fieldnames = ["formula_name", "result", "time_seconds", "mode"]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nExecution finished! Results saved to:\n{output_csv}")

if __name__ == "__main__":
    run_all_interesting_incremental()