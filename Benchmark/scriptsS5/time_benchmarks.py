import subprocess
import os
import sys
import csv
import argparse
import re
import statistics
import concurrent.futures

ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(ruta_raiz)

import S5.parser_s5 as s5parser
import S5.NNFVisitor as tonnf
import S5.DiamondVisitor as diamond_counter
import S5.AST_S5 as ast_s5

sys.setrecursionlimit(10000)

# CARPETA PARA LOS RESULTADOS
OUTPUT_DIR = "tiempos_comparacion"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


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
        with open(file_path, "r") as f:
            formula_str = f.read()

        parsed = s5parser.parse(formula_str)
        boxes, diamonds = count_operators(parsed)

        nnf_form = parsed.accept(tonnf.ToNNF())
        mundos = nnf_form.accept(diamond_counter.DiamondVisitor()) + 1

        return mundos, boxes, diamonds
    except Exception as e:
        print(f"Error analizando {file_path}: {e}")
        return -1, -1, -1


def parse_solver_output(output, metrics, results):
    """Extrae todos los tiempos desglosados del solver."""
    for line in output.splitlines():
        if "Parse time:" in line:
            metrics["parse"].append(float(re.search(r"Parse time:\s*([0-9.]+)", line).group(1)))
        elif "NNF time:" in line:
            metrics["nnf"].append(float(re.search(r"NNF time:\s*([0-9.]+)", line).group(1)))
        elif "To SAT time:" in line:
            metrics["to_sat"].append(float(re.search(r"To SAT time:\s*([0-9.]+)", line).group(1)))
        elif "Translation time:" in line:
            metrics["translation"].append(float(re.search(r"Translation time:\s*([0-9.]+)", line).group(1)))
        elif "Z3 time:" in line:
            metrics["z3"].append(float(re.search(r"Z3 time:\s*([0-9.]+)", line).group(1)))
        elif "Total time:" in line:
            metrics["total"].append(float(re.search(r"Total time:\s*([0-9.]+)", line).group(1)))
        elif "SAT" in line or "UNSAT" in line or "unsat" in line:
            results.append("SAT" if "SAT" in line else "UNSAT")


def run_solver(instance_path, metrics, results):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        solver_path = os.path.abspath(os.path.join(base_dir, "../../s5_solver.py"))
        
        process = subprocess.run(
            [sys.executable, solver_path, "-f", instance_path],
            timeout=900,
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            print(f"Error en solver para {instance_path}: {process.stderr}")
            return False
            
        parse_solver_output(process.stdout, metrics, results)
        return False
    except subprocess.TimeoutExpired:
        return True
    except Exception as e:
        print(f"Error ejecutando solver: {e}")
        return False


def calculate_median(times):
    if times:
        return str(round(statistics.median(times), 6))
    return "900"


def process_single_file(file, runs):
    row = {}
    instance = file.replace(".s5", "").split("-")
    row["form"] = instance[0].replace("formula", "")
    row["n"] = int(instance[1])
    row["m"] = int(instance[2])
    row["l"] = int(instance[3])
    row["ratio"] = round(row["m"] / row["n"], 2)
    
    # Asignamos D_target y B_target directamente a diamonds y boxes
    row["diamonds"] = int(instance[4])
    row["boxes"] = int(instance[5])

    base_dir = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.abspath(os.path.join(base_dir, "../formulasS5/", file))
    
    mundos, _, _ = analyze_formula(instance_path)
    row["worlds"] = mundos
    row["modal_ratio"] = round(row["diamonds"] / row["boxes"], 3) if row["boxes"] > 0 else 999.9

    metrics = {
        "parse": [], "nnf": [], "to_sat": [], 
        "translation": [], "z3": [], "total": []
    }
    results = []
    timed_out = False

    for _ in range(runs):
        if run_solver(instance_path, metrics, results):
            timed_out = True

    row["parse_time"] = calculate_median(metrics["parse"])
    row["nnf_time"] = calculate_median(metrics["nnf"])
    row["tosat_time"] = calculate_median(metrics["to_sat"])
    row["translation_time"] = calculate_median(metrics["translation"])
    row["z3_time"] = calculate_median(metrics["z3"])
    row["total_time"] = calculate_median(metrics["total"])
    
    row["result"] = results[0] if results else ("TO" if timed_out else "ERR")
    row["size"] = os.path.getsize(instance_path) if os.path.exists(instance_path) else 0

    return row


def load_processed_formulas(csv_filename):
    processed_formulas = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                formula_key = f"{row['form']}-{row['n']}-{row['m']}-{row['l']}-{row['diamonds']}-{row['boxes']}"
                processed_formulas.add(formula_key)
    return processed_formulas


def get_files_to_process(batch_num, processed_formulas):
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)\.s5$")
    files_to_process = []
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    formulas_dir = os.path.abspath(os.path.join(base_dir, "../formulasS5/"))

    if not os.path.exists(formulas_dir):
        print(f"⚠️ ERROR: No se encontró el directorio {formulas_dir}")
        return files_to_process

    for filename in os.listdir(formulas_dir):
        match = pattern.match(filename)
        if not match:
            continue
        inst_id = int(match.group(1))
        if inst_id != batch_num:
            continue
            
        parts = filename.replace(".s5", "").split("-")
        formula_key = f"{parts[0].replace('formula', '')}-{parts[1]}-{parts[2]}-{parts[3]}-{parts[4]}-{parts[5]}"

        if formula_key not in processed_formulas:
            files_to_process.append(filename)

    return files_to_process


def process_batch(batch_num, runs):
    csv_filename = os.path.join(OUTPUT_DIR, f"output-batch{batch_num}.csv")

    processed_formulas = load_processed_formulas(csv_filename)
    print(f"Batch {batch_num}: Found {len(processed_formulas)} Solved formulas. Omitting...")

    files_to_process = get_files_to_process(batch_num, processed_formulas)
    total_files_batch = len(files_to_process)
    if total_files_batch == 0:
        return

    cores = max(1, os.cpu_count() - 1)
    print(f"Batch {batch_num}: Processing {total_files_batch} formulas in {cores} threads...")

    fieldnames = [
        "form", "n", "m", "l", "ratio",
        "worlds", "boxes", "diamonds", "modal_ratio",
        "parse_time", "nnf_time", "tosat_time", 
        "translation_time", "z3_time", "total_time",
        "result", "size"
    ]
    
    write_header = not os.path.exists(csv_filename) or os.path.getsize(csv_filename) == 0

    with open(csv_filename, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        processed_count = 0
        with concurrent.futures.ProcessPoolExecutor(max_workers=cores) as executor:
            futures = {
                executor.submit(process_single_file, f, runs): f
                for f in files_to_process
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    writer.writerow(future.result())
                    csvfile.flush()
                except Exception as exc:
                    print(f"Exception: {exc}")

                processed_count += 1
                if processed_count % 5 == 0 or processed_count == total_files_batch:
                    progress = (processed_count / total_files_batch) * 100
                    print(f"Progress Batch {batch_num}: {round(progress, 1)}%")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--all", action="store_true", default=False)
    parser.add_argument("--runs", type=int, default=1)
    args = parser.parse_args()

    if not args.all:
        process_batch(args.batch, args.runs)
    else:
        for i in range(1, 11):
            process_batch(i, args.runs)


if __name__ == "__main__":
    main()