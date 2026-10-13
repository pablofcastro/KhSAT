"""
Benchmark script to compare S5cheetah (C++ executable) against KhSAT (s5_solver_dcc.py).
Parses outputs from both solvers, compares SAT/UNSAT soundness, generated Kripke worlds,
solver time, total execution time, and independent Kripke Model Verification for SAT.
"""

import argparse
import concurrent.futures
import csv
import os
import re
import statistics
import subprocess
import sys

# Recursion limit extension for deep formula parsing
sys.setrecursionlimit(100000)

OUTPUT_DIR = "tiempos_comparacion"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def run_khsat(solver_path, instance_path, timeout):
    """
    Executes Python s5_solver_dcc.py on a formula instance.
    Returns a dictionary with parsed metrics or TIMEOUT/ERROR status.
    """
    res = {
        "result": "ERR",
        "worlds": -1,
        "to_sat_time": -1.0,
        "z3_time": -1.0,
        "total_time": -1.0,
        "model_verified": None,  # <- NUEVO: Guarda el resultado del Model Checker
    }

    cmd = [sys.executable, solver_path, "--intohylo", "-f", instance_path]

    try:
        process = subprocess.run(
            cmd, timeout=timeout, capture_output=True, text=True
        )

        if process.returncode != 0:
            return res

        output = process.stdout
        for line in output.splitlines():
            if "DCC Worlds:" in line:
                m = re.search(r"DCC Worlds:\s*(\d+)", line)
                if m:
                    res["worlds"] = int(m.group(1))
            elif "To SAT time:" in line:
                m = re.search(r"To SAT time:\s*([0-9.]+)", line)
                if m:
                    res["to_sat_time"] = float(m.group(1))
            elif "Z3 time:" in line:
                m = re.search(r"Z3 time:\s*([0-9.]+)", line)
                if m:
                    res["z3_time"] = float(m.group(1))
            elif "Total time:" in line:
                m = re.search(r"Total time:\s*([0-9.]+)", line)
                if m:
                    res["total_time"] = float(m.group(1))
            elif "The formula is SAT." in line:
                res["result"] = "SAT"
            elif "The formula is unsat." in line:
                res["result"] = "UNSAT"
            # <- NUEVO: Parseo de la salida del Model Checker
            elif "Model Checker: VERIFIED" in line:
                res["model_verified"] = True
            elif "Model Checker: FAILED" in line:
                res["model_verified"] = False

        return res

    except subprocess.TimeoutExpired:
        res["result"] = "TO"
        res["total_time"] = float(timeout)
        return res
    except Exception as e:
        print(f"Error running KhSAT on {os.path.basename(instance_path)}: {e}")
        return res


def run_cheetah(cheetah_bin, instance_path, timeout):
    """
    Executes Cheetah2.0 C++ executable on a formula instance.
    Parses outputs (converting ms to seconds).
    """
    res = {
        "result": "ERR",
        "worlds": -1,
        "to_sat_time": -1.0,
        "sat_time": -1.0,
        "total_time": -1.0,
    }

    cmd = [cheetah_bin, instance_path]
    env = os.environ.copy()

    try:
        process = subprocess.run(
            cmd, timeout=timeout, capture_output=True, text=True, env=env
        )

        output = process.stdout
        for line in output.splitlines():
            if "possible worlds:" in line:
                m = re.search(r"possible worlds:\s*(\d+)", line)
                if m:
                    res["worlds"] = int(m.group(1))
            elif "Tran2SAT_time(ms):" in line:
                m = re.search(r"Tran2SAT_time\(ms\):\s*([0-9.]+)", line)
                if m:
                    res["to_sat_time"] = float(m.group(1)) / 1000.0
            elif "SAT-Solver time" in line:
                m = re.search(r"SAT-Solver time\s*:\s*([0-9.]+)\s*ms", line)
                if m:
                    res["sat_time"] = float(m.group(1)) / 1000.0
            elif "Total_time(ms):" in line:
                m = re.search(r"Total_time\(ms\):\s*([0-9.]+)", line)
                if m:
                    res["total_time"] = float(m.group(1)) / 1000.0
            elif "s SATISFIABLE" in line or "SATISFIABLE" in line:
                res["result"] = "SAT"
            elif "s UNSATISFIABLE" in line or "UNSATISFIABLE" in line:
                res["result"] = "UNSAT"

        return res

    except subprocess.TimeoutExpired:
        res["result"] = "TO"
        res["total_time"] = float(timeout)
        return res
    except Exception as e:
        print(
            f"Error running Cheetah on {os.path.basename(instance_path)}: {e}"
        )
        return res


def process_single_file(filename, directory_path, cheetah_bin, solver_path, runs, timeout):
    """
    Executes both solvers on a single formula file and aggregates comparative statistics.
    """
    instance_path = os.path.join(directory_path, filename)

    khsat_runs = []
    cheetah_runs = []

    for _ in range(runs):
        khsat_runs.append(run_khsat(solver_path, instance_path, timeout))
        cheetah_runs.append(run_cheetah(cheetah_bin, instance_path, timeout))

    res_khsat = khsat_runs[0]["result"]
    res_cheetah = cheetah_runs[0]["result"]
    model_verified = khsat_runs[0]["model_verified"]  # <- NUEVO

    match = False
    if res_khsat in ["SAT", "UNSAT"] and res_cheetah in ["SAT", "UNSAT"]:
        match = (res_khsat == res_cheetah)
        if not match:
            print(
                f"\n⚠️ MISMATCH in {filename}: KhSAT={res_khsat} vs Cheetah={res_cheetah}\n"
            )

    def get_median(runs_list, key):
        vals = [r[key] for r in runs_list if r[key] >= 0]
        return round(statistics.median(vals), 6) if vals else -1.0

    worlds_khsat = khsat_runs[0]["worlds"]
    worlds_cheetah = cheetah_runs[0]["worlds"]

    total_time_khsat = get_median(khsat_runs, "total_time")
    z3_time_khsat = get_median(khsat_runs, "z3_time")

    total_time_cheetah = get_median(cheetah_runs, "total_time")
    sat_time_cheetah = get_median(cheetah_runs, "sat_time")

    speedup = -1.0
    if total_time_khsat > 0 and total_time_cheetah > 0:
        speedup = round(total_time_cheetah / total_time_khsat, 3)

    return {
        "instance": filename,
        "res_khsat": res_khsat,
        "res_cheetah": res_cheetah,
        "match": match,
        "model_verified": model_verified,  # <- NUEVO
        "worlds_khsat": worlds_khsat,
        "worlds_cheetah": worlds_cheetah,
        "z3_time_khsat": z3_time_khsat,
        "sat_time_cheetah": sat_time_cheetah,
        "total_time_khsat": total_time_khsat,
        "total_time_cheetah": total_time_cheetah,
        "speedup_khsat_vs_cheetah": speedup,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run S5cheetah vs KhSAT comparison on benchmark formulas."
    )
    parser.add_argument(
        "--folder",
        type=str,
        default="formulasCheetahS5",
        help="Folder containing formulas (relative to project root or absolute)",
    )
    parser.add_argument(
        "--cheetah-bin",
        type=str,
        default="./Cheetah2.0",
        help="Path to Cheetah2.0 executable",
    )
    parser.add_argument(
        "--solver-script",
        type=str,
        default="s5_solver_dcc.py",
        help="Path to KhSAT DCC solver script",
    )
    parser.add_argument(
        "--runs", type=int, default=1, help="Executions per formula for median time"
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Timeout in seconds per solver run"
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, "../.."))

    if os.path.isabs(args.folder):
        formulas_dir = args.folder
    else:
        formulas_dir = os.path.abspath(os.path.join(root_dir, args.folder))

    if os.path.isabs(args.solver_script):
        solver_path = args.solver_script
    else:
        solver_path = os.path.abspath(os.path.join(root_dir, args.solver_script))

    if os.path.isabs(args.cheetah_bin):
        cheetah_bin = args.cheetah_bin
    else:
        cheetah_bin = os.path.abspath(os.path.join(root_dir, args.cheetah_bin))

    if not os.path.exists(formulas_dir):
        print(f"❌ Error: Formulas directory not found at {formulas_dir}")
        sys.exit(1)

    if not os.path.exists(solver_path):
        print(f"❌ Error: Solver script not found at {solver_path}")
        sys.exit(1)

    if not os.path.exists(cheetah_bin):
        print(f"❌ Error: Cheetah binary not found at {cheetah_bin}")
        sys.exit(1)

    files = [
        f
        for f in os.listdir(formulas_dir)
        if f.endswith(".s5") or f.endswith(".intohylo")
    ]
    total_files = len(files)

    if total_files == 0:
        print(f"No .s5 or .intohylo benchmark files found in {formulas_dir}")
        sys.exit(1)

    csv_filename = os.path.join(OUTPUT_DIR, "cheetah_vs_khsat.csv")
    cores = max(1, os.cpu_count() - 1)

    print(f"🚀 Starting benchmark comparison:")
    print(f" - Formulas folder: {formulas_dir} ({total_files} files)")
    print(f" - KhSAT script:    {solver_path}")
    print(f" - Cheetah binary:  {cheetah_bin}")
    print(f" - Parallel cores:  {cores}")
    print(f" - Output CSV:       {csv_filename}\n")

    # <- NUEVO: Se añade "model_verified" a las columnas del CSV
    fieldnames = [
        "instance",
        "res_khsat",
        "res_cheetah",
        "match",
        "model_verified",
        "worlds_khsat",
        "worlds_cheetah",
        "z3_time_khsat",
        "sat_time_cheetah",
        "total_time_khsat",
        "total_time_cheetah",
        "speedup_khsat_vs_cheetah",
    ]

    mismatches = 0
    khsat_wins = 0
    cheetah_wins = 0
    verified_models = 0  # <- NUEVO

    with open(csv_filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        processed_count = 0
        with concurrent.futures.ProcessPoolExecutor(max_workers=cores) as executor:
            futures = {
                executor.submit(
                    process_single_file,
                    f,
                    formulas_dir,
                    cheetah_bin,
                    solver_path,
                    args.runs,
                    args.timeout,
                ): f
                for f in files
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    row = future.result()
                    writer.writerow(row)
                    csvfile.flush()

                    if row["match"] is False:
                        mismatches += 1

                    if row["model_verified"] is True:
                        verified_models += 1

                    if row["total_time_khsat"] > 0 and row["total_time_cheetah"] > 0:
                        if row["total_time_khsat"] < row["total_time_cheetah"]:
                            khsat_wins += 1
                        else:
                            cheetah_wins += 1

                except Exception as exc:
                    print(f"Exception generated during execution: {exc}")

                processed_count += 1
                if processed_count % 5 == 0 or processed_count == total_files:
                    progress = (processed_count / total_files) * 100
                    print(
                        f"Progress: {round(progress, 1)}% ({processed_count}/{total_files})"
                    )

    print("\n" + "=" * 60)
    print(" SUMMARY RESULTS")
    print("=" * 60)
    print(f" Total formulas processed: {total_files}")
    print(f" Verdict Matches:          {total_files - mismatches}/{total_files}")
    print(f" SAT Models Verified:      {verified_models}")  # <- NUEVO
    print(f" KhSAT Total Wins:         {khsat_wins}")
    print(f" Cheetah Total Wins:       {cheetah_wins}")
    if mismatches > 0:
        print(f" ❌ Mismatches:            {mismatches}")
    else:
        print(" ✅ Soundness Verification: 100% Verdict Match")
    print("=" * 60)


if __name__ == "__main__":
    main()