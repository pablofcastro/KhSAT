import argparse
import concurrent.futures
import csv
import os
import re
import statistics
import subprocess
import sys

# Ajuste de ruta para localizar los módulos de S5
ruta_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(ruta_raiz)

import S5.AST_S5 as ast_s5
import S5.DiamondVisitor as diamond_counter
import S5.NNFVisitor as tonnf
import S5.parser_s5 as s5parser

sys.setrecursionlimit(100000)

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
    """Extrae tiempos y veredicto del output de un solver."""
    for line in output.splitlines():
        if "Parse time:" in line:
            metrics["parse"].append(
                float(re.search(r"Parse time:\s*([0-9.]+)", line).group(1))
            )
        elif "NNF time:" in line or "NNF/Simplify time:" in line:
            metrics["nnf"].append(
                float(
                    re.search(
                        r"(?:NNF|NNF/Simplify) time:\s*([0-9.]+)", line
                    ).group(1)
                )
            )
        elif "To SAT time:" in line:
            metrics["to_sat"].append(
                float(re.search(r"To SAT time:\s*([0-9.]+)", line).group(1))
            )
        elif "Translation time:" in line:
            metrics["translation"].append(
                float(re.search(r"Translation time:\s*([0-9.]+)", line).group(1))
            )
        elif "Z3 time:" in line:
            metrics["z3"].append(
                float(re.search(r"Z3 time:\s*([0-9.]+)", line).group(1))
            )
        elif "Total time:" in line:
            metrics["total"].append(
                float(re.search(r"Total time:\s*([0-9.]+)", line).group(1))
            )
        elif "SAT" in line or "UNSAT" in line or "unsat" in line:
            results.append("SAT" if "SAT" in line else "UNSAT")


def run_single_solver(solver_script_name, instance_path, metrics, results):
    """Ejecuta un script específico de solver (s5_solver.py o s5_solver_dcc.py)."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        solver_path = os.path.abspath(
            os.path.join(base_dir, "../../", solver_script_name)
        )

        process = subprocess.run(
            [sys.executable, solver_path, "-f", instance_path],
            timeout=900,
            capture_output=True,
            text=True,
        )

        if process.returncode != 0:
            print(
                f"Error en {solver_script_name} para {instance_path}: {process.stderr}"
            )
            return False

        parse_solver_output(process.stdout, metrics, results)
        return False
    except subprocess.TimeoutExpired:
        return True
    except Exception as e:
        print(f"Error ejecutando {solver_script_name}: {e}")
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

    row["diamonds"] = int(instance[4])
    row["boxes"] = int(instance[5])

    base_dir = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.abspath(
        os.path.join(base_dir, "../formulasS5/", file)
    )

    mundos, _, _ = analyze_formula(instance_path)
    row["worlds"] = mundos
    row["modal_ratio"] = (
        round(row["diamonds"] / row["boxes"], 3) if row["boxes"] > 0 else 999.9
    )

    # Metrics y resultados para el solver Base (s5_solver.py)
    metrics_base = {
        "parse": [],
        "nnf": [],
        "to_sat": [],
        "translation": [],
        "z3": [],
        "total": [],
    }
    results_base = []
    to_base = False

    # Metrics y resultados para el solver DCC (s5_solver_dcc.py)
    metrics_dcc = {
        "parse": [],
        "nnf": [],
        "to_sat": [],
        "translation": [],
        "z3": [],
        "total": [],
    }
    results_dcc = []
    to_dcc = False

    for _ in range(runs):
        if run_single_solver(
            "s5_solver.py", instance_path, metrics_base, results_base
        ):
            to_base = True
        if run_single_solver(
            "s5_solver_dcc.py", instance_path, metrics_dcc, results_dcc
        ):
            to_dcc = True

    # Asignación de resultados finales
    res_base = (
        results_base[0] if results_base else ("TO" if to_base else "ERR")
    )
    res_dcc = results_dcc[0] if results_dcc else ("TO" if to_dcc else "ERR")

    row["res_base"] = res_base
    row["res_dcc"] = res_dcc

    # Comparación de coincidencia entre ambos solvers
    if res_base in ["SAT", "UNSAT"] and res_dcc in ["SAT", "UNSAT"]:
        row["match"] = res_base == res_dcc
        if res_base != res_dcc:
            print(
                f"⚠️ DISCREPANCIA DETECTADA en {file}: Base={res_base} vs DCC={res_dcc}"
            )
    else:
        row["match"] = "TIMEOUT/ERR"

    # Tiempos de s5_solver.py
    row["z3_time_base"] = calculate_median(metrics_base["z3"])
    row["total_time_base"] = calculate_median(metrics_base["total"])

    # Tiempos de s5_solver_dcc.py
    row["z3_time_dcc"] = calculate_median(metrics_dcc["z3"])
    row["total_time_dcc"] = calculate_median(metrics_dcc["total"])

    row["size"] = (
        os.path.getsize(instance_path) if os.path.exists(instance_path) else 0
    )

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
    csv_filename = os.path.join(
        OUTPUT_DIR, f"output-comparison-batch{batch_num}.csv"
    )

    processed_formulas = load_processed_formulas(csv_filename)
    print(
        f"Batch {batch_num}: Found {len(processed_formulas)} already compared formulas. Omitting..."
    )

    files_to_process = get_files_to_process(batch_num, processed_formulas)
    total_files_batch = len(files_to_process)
    if total_files_batch == 0:
        return

    cores = max(1, os.cpu_count() - 1)
    print(
        f"Batch {batch_num}: Comparing {total_files_batch} formulas across both solvers using {cores} workers..."
    )

    fieldnames = [
        "form",
        "n",
        "m",
        "l",
        "ratio",
        "worlds",
        "boxes",
        "diamonds",
        "modal_ratio",
        "res_base",
        "res_dcc",
        "match",
        "z3_time_base",
        "total_time_base",
        "z3_time_dcc",
        "total_time_dcc",
        "size",
    ]

    write_header = (
        not os.path.exists(csv_filename)
        or os.path.getsize(csv_filename) == 0
    )

    mismatches = 0
    with open(csv_filename, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()

        processed_count = 0
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=cores
        ) as executor:
            futures = {
                executor.submit(process_single_file, f, runs): f
                for f in files_to_process
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    result_row = future.result()
                    writer.writerow(result_row)
                    csvfile.flush()

                    if result_row["match"] is False:
                        mismatches += 1

                except Exception as exc:
                    print(f"Exception: {exc}")

                processed_count += 1
                if (
                    processed_count % 5 == 0
                    or processed_count == total_files_batch
                ):
                    progress = (processed_count / total_files_batch) * 100
                    print(
                        f"Progress Batch {batch_num}: {round(progress, 1)}%"
                    )

    if mismatches > 0:
        print(
            f"❌ Batch {batch_num} finalizado con {mismatches} discrepancias de resultado."
        )
    else:
        print(
            f"✅ Batch {batch_num} finalizado: 100% de coincidencias en veredictos entre ambos solvers."
        )


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