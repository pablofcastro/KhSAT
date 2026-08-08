import subprocess
import os
import sys
import csv
import argparse
import re
import statistics

def process_batch(i, runs) :
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+)-(\d+)-([\d.]+).s5$")
    files = []
    size = 0
    for filename in os.listdir(f"../formulasS5/"):
        size = size + 1
        m = pattern.match(filename)
        if m:
            n = int(m.group(1))
            if n < i*10 and n >= (i-1)*10 :
                files.append(filename)
    result = {}
    result = [] # the result is a list of dics, each dict is a row
    total_files = len(files)
    processed = 0
    for file in files :
        row = {}
        instance = file.replace(".s5","").split('-')
        row["form"] = instance[0]
        row["n"] = instance[1] # number of variables
        row["m"] = instance[2] # number of clauses
        row["ratio"] = round(int(instance[2])/int(instance[1]), 2) # clauses per variable
        row["p"] = instance[4] # diamond degree parameter
        instance_path = os.path.join(f"../formulasS5/", file)
        print(f"Running: python s5_solver.py -f {instance_path}")
        times = []
        results = []
        timed_out = False
        for r in range(runs) :
            try :
                output = subprocess.run([sys.executable, "../../s5_solver.py", "-f", instance_path], timeout=900, capture_output=True).stdout.decode()
                lines = output.splitlines()
                for line in lines :
                    if "Time:" in line :
                        times.append(float(line.split()[1]))
                    elif "SAT" in line or "unsat" in line :
                        results.append("SAT" if "SAT" in line else "UNSAT")
            except Exception as e:
                print(f'Error running: {instance_path}:'+str(e))
                timed_out = True
        row["time"] = str(statistics.median(times)) if times else "900" # median execution time
        row["result"] = results[0] if results else ("TO" if timed_out else "TO")
        row["size"] = os.path.getsize(instance_path) # formula length in bytes
        processed = processed + 1
        print(f"Progress: {round((processed/total_files) * 100,1)}%")
        result.append(row)

    if result :
        fieldnames = result[0].keys()
    else :
        fieldnames = ["form", "n", "m", "ratio", "p", "time", "result", "size"]

    # Write to CSV
    with open(f"output-batch{i}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()     # write header row
        writer.writerows(result)   # write data rows

if __name__ == "__main__" :
    parser = argparse.ArgumentParser(description="Process the formulas in batches.")

    parser.add_argument(
        "--batch",
        type=int,
        default=10,
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
    if  not args.all :
        print(f"Processing batch: {args.batch}")
        process_batch(args.batch, args.runs)
        print(f"Result written in output-batch{args.batch}.csv")
    else :
        for i in [1,2,3,4,5] :
            print("Processing all the formulas")
            process_batch(i, args.runs)