import subprocess
import os
import sys
import csv
import argparse
import re
import statistics
import concurrent.futures

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
import S5.DiamondVisitor as diamond_counter
import S5.parser_s5 as s5parser

def count_worlds(instance_path):
    sys.setrecursionlimit(10000)
    try:
        with open(instance_path, "r") as f:
            text = f.read()
        parsed = s5parser.parse(text)
        n = parsed.accept(diamond_counter.DiamondVisitor())
        return n + 1
    except Exception as e:
        print(f"Warning: could not compute worlds for {instance_path}: {e}")
        return ""

def process_single_file(file, runs):
    """Esta función procesa una sola fórmula. Será ejecutada en paralelo por los distintos núcleos."""
    row = {}
    instance = file.replace(".s5","").split('-')
    row["form"] = instance[0]
    row["n"] = instance[1] # number of variables
    row["m"] = instance[2] # number of clauses
    row["ratio"] = round(int(instance[2])/int(instance[1]), 2) # clauses per variable
    row["p"] = instance[4] # diamond degree parameter
    
    instance_path = os.path.join("../formulasS5/", file)
    row["worlds"] = count_worlds(instance_path)
    
    times = []
    results = []
    timed_out = False
    
    for r in range(runs) :
        try :
            # Ejecutamos el solver
            output = subprocess.run([sys.executable, "../../s5_solver.py", "-f", instance_path], timeout=900, capture_output=True).stdout.decode()
            lines = output.splitlines()
            for line in lines :
                if "Time:" in line :
                    times.append(float(line.split()[1]))
                elif "SAT" in line or "UNSAT" in line or "unsat" in line :
                    results.append("SAT" if "SAT" in line else "UNSAT")
        except Exception as e:
            # Capturamos si Z3 explota o da Timeout
            timed_out = True
            
    row["time"] = str(statistics.median(times)) if times else "900" # median execution time
    row["result"] = results[0] if results else ("TO" if timed_out else "TO")
    row["size"] = os.path.getsize(instance_path) # formula length in bytes
    
    return row

def process_batch(batch_num, runs) :
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+)-(\d+)-([\d.]+).s5$")
    files = []
    
    for filename in os.listdir("../formulasS5/"):
        m = pattern.match(filename)
        if m:
            # m.group(1) captura el ID de la instancia (ej. el '2' de formula2-...)
            inst_id = int(m.group(1))
            if inst_id < batch_num*10 and inst_id >= (batch_num-1)*10 :
                files.append(filename)
                
    total_files = len(files)
    if total_files == 0:
        print(f"No files found for batch {batch_num}.")
        return

    # Imprimimos cuántos núcleos va a usar
    cores = os.cpu_count()
    print(f"Batch {batch_num}: Processing {total_files} files in PARALLEL using {cores} CPU cores...")
    
    result = []
    processed = 0
    
    # AQUÍ SUCEDE LA MAGIA DEL PARALELISMO
    with concurrent.futures.ProcessPoolExecutor(max_workers=cores) as executor:
        # Enviamos todas las fórmulas a la piscina de procesos
        futures = {executor.submit(process_single_file, f, runs): f for f in files}
        
        # A medida que se van terminando (sin importar el orden), las guardamos
        for future in concurrent.futures.as_completed(futures):
            try:
                row_data = future.result()
                result.append(row_data)
            except Exception as exc:
                print(f"A file generated an exception: {exc}")
                
            processed += 1
            # Imprimimos progreso cada 10 archivos para no saturar la consola
            if processed % 10 == 0 or processed == total_files:
                print(f"Progress Batch {batch_num}: {round((processed/total_files) * 100, 1)}% ({processed}/{total_files})")

    # Si hay resultados, tomamos los fieldnames del primer diccionario
    if result :
        fieldnames = result[0].keys()
    else :
        fieldnames = ["form", "n", "m", "ratio", "p", "worlds", "time", "result", "size"]

    # Write to CSV
    with open(f"output-batch{batch_num}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()     # write header row
        writer.writerows(result)   # write data rows

if __name__ == "__main__" :
    parser = argparse.ArgumentParser(description="Process the formulas in batches.")

    parser.add_argument(
        "--batch",
        type=int,
        default=3,
        help="The batch to be processed: 1,2,3,4,5"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Option to process all the batches"
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of solver executions per formula to compute the median time"
    )
    args = parser.parse_args()
    
    if not args.all :
        print(f"Processing batch: {args.batch}")
        process_batch(args.batch, args.runs)
        print(f"Result written in output-batch{args.batch}.csv")
    else :
        # Hacemos los 5 batches
        for i in [1,2,3,4,5] :
            print(f"--- Starting Batch {i} ---")
            process_batch(i, args.runs)