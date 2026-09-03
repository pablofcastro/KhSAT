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


def count_operators(node):
    """This function counts the number of boxes and diamonds in a given AST node.

    Args:
        node: The node of the AST to count operators in.

    Returns:
        tuple: A tuple containing the number of boxes and diamonds in the node.
    """
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
    """The analysis of the formula is responsible for obtaining information about its composition.

    Args:
        file_path: The path to the S5 formula file.

    Returns:
        tuple: A tuple containing the number of worlds, boxes, and diamonds in the formula.
    """

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


def parse_solver_output(output, translation_times, z3_times, total_times, results):
    """This method parse the output of the solver and extract the relevant information.

    Args:
        output: The output string from the solver.
        translation_times: A list to store translation times.
        z3_times: A list to store Z3 solving times.
        total_times: A list to store total times.
        results: A list to store the results of the solver.
    """
    for line in output.splitlines():
        if "Translation time:" in line:
            match = re.search(r"Translation time:\s*([0-9.]+)", line)
            if match:
                translation_times.append(float(match.group(1)))
        elif "Z3 time:" in line:
            match = re.search(r"Z3 time:\s*([0-9.]+)", line)
            if match:
                z3_times.append(float(match.group(1)))
        elif "Total time:" in line:
            match = re.search(r"Total time:\s*([0-9.]+)", line)
            if match:
                total_times.append(float(match.group(1)))
        elif "SAT" in line or "UNSAT" in line or "unsat" in line:
            results.append("SAT" if "SAT" in line else "UNSAT")


def run_solver(instance_path, translation_times, z3_times, total_times, results):
    """The method run solver this encharged for execute a sat solver for s5.

    Args:
        instance_path: The path to the S5 formula file.
        translation_times: A list to store translation times.
        z3_times: A list to store Z3 solving times.
        total_times: A list to store total times.
        results: A list to store the results of the solver.


    Returns:
        bool: True if the solver timed out, False otherwise.
    """
    try:
        output = subprocess.run(
            [sys.executable, "../../s5_solver.py", "-f", instance_path],
            timeout=900,
            capture_output=True,
        ).stdout.decode()
        parse_solver_output(output, translation_times, z3_times, total_times, results)
        return False
    except subprocess.TimeoutExpired:
        return True
    except Exception as e:
        print(f"Error ejecutando solver: {e}")
        return False


def calculate_median(times):
    """This method calculate a median time.

    Args:
        times: A list of times to calculate the median from.

    Returns:
        str: The median time as a string, or "900" if the list is empty.
    """
    if times:
        return str(round(statistics.median(times), 6))
    return "900"


def process_single_file(file, runs):
    """Process a single S5 formula file and execute the solver.

    Args:
        file (str): The path to the S5 formula file.
        runs (int): The number of times to run the solver.

    Returns:
        dict: A dictionary containing the results of the analysis and solving.
    """
    row = {}
    instance = file.replace(".s5", "").split("-")
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
    row["modal_ratio"] = round(diamonds / boxes, 3) if boxes > 0 else 999.9

    # Execute solver
    translation_times = []
    z3_times = []
    total_times = []
    results = []
    timed_out = False

    for _ in range(runs):
        if run_solver(instance_path, translation_times, z3_times, total_times, results):
            timed_out = True

    # Time for traduction S5 to propositional formula
    row["translation_time"] = calculate_median(translation_times)
    # Time for Z3 to solve the propositional formula
    row["z3_time"] = calculate_median(z3_times)

    # Total time for resolve the formula
    row["total_time"] = calculate_median(total_times)
    row["time"] = row["total_time"]
    row["result"] = results[0] if results else ("TO" if timed_out else "ERR")
    row["size"] = os.path.getsize(instance_path)

    return row


def load_processed_formulas(csv_filename):
    """This function loads the processed formulas from a CSV file and returns a set of formula keys.

    Args:
        csv_filename (str): The filename of the CSV file containing processed formulas.

    Returns:
        set: A set of formula keys that have been processed.
    """
    processed_formulas = set()

    if os.path.exists(csv_filename):
        with open(csv_filename, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                formula_key = (
                    f"{row['form']}-"
                    f"{row['n']}-"
                    f"{row['m']}-"
                    f"{row['l']}-"
                    f"{row['D_target']}-"
                    f"{row['B_target']}"
                )
                processed_formulas.add(formula_key)
    return processed_formulas


def get_files_to_process(batch_num, processed_formulas):
    """This function retrieves the list of formula files to process for a given batch number, excluding those that have already been processed.

    Args:
        batch_num (int): The batch number to process.
        processed_formulas (set): A set of formula keys that have already been processed.

    Returns:
        list: A list of filenames for the formulas to process.
    """

    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+)-(\d+)-(\d+)-(\d+)\.s5$")
    files_to_process = []

    for filename in os.listdir("../formulasS5/"):
        match = pattern.match(filename)
        if not match:
            continue
        inst_id = int(match.group(1))
        if inst_id != batch_num:
            continue
        parts = filename.replace(".s5", "").split("-")
        formula_key = (
            f"{parts[0].replace('formula', '')}-"
            f"{parts[1]}-"
            f"{parts[2]}-"
            f"{parts[3]}-"
            f"{parts[4]}-"
            f"{parts[5]}"
        )

        if formula_key not in processed_formulas:
            files_to_process.append(filename)

    return files_to_process


def process_batch(batch_num, runs):
    """This function processes a batch of formulas, running the solver on each formula and recording the results in a CSV file.

    Args:
        batch_num (int): The batch number to process.
        runs (int): The number of runs to perform.
    """
    csv_filename = f"output-batch{batch_num}.csv"

    # Processed formulas
    processed_formulas = load_processed_formulas(csv_filename)
    print(
        f"Batch {batch_num}: Found "
        f"{len(processed_formulas)} Solved formulas. "
        f"Omitting..."
    )

    # Find new formulas
    files_to_process = get_files_to_process(batch_num, processed_formulas)
    total_files_batch = len(files_to_process)
    if total_files_batch == 0:
        return

    # Workers
    cores = max(1, os.cpu_count() - 1)
    print(
        f"Batch {batch_num}: Processing "
        f"{total_files_batch} formulas "
        f"in {cores} threads..."
    )

    fieldnames = [
        "form",
        "n",
        "m",
        "l",
        "ratio",
        "D_target",
        "B_target",
        "worlds",
        "boxes",
        "diamonds",
        "modal_ratio",
        "translation_time",
        "z3_time",
        "total_time",
        "time",
        "result",
        "size",
    ]
    write_header = (
        not os.path.exists(csv_filename) or os.path.getsize(csv_filename) == 0
    )

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
                    print(f"Progress Batch {batch_num}: " f"{round(progress, 1)}%")


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
