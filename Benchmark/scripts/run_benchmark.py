import subprocess
import os
import csv
import argparse
import re
import sys

def process_batch(i, formulas_dir="../formulas/") :
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+).kh$")
    files = []
    size = 0
    if not os.path.exists(formulas_dir):
        print(f"Directory not found: {formulas_dir}")
        return
    for filename in os.listdir(formulas_dir):
        size = size + 1
        m = pattern.match(filename)
        if m:
            n = int(m.group(1))
            if n < i*10 and n >= (i-1)*10 :
                files.append(filename)
    result = {}
    result = [] # the result is a list of dics, each dict is a row
    total_files = len(files)
    if total_files == 0:
        print(f"No files found for batch {i} in directory {formulas_dir}")
        return
    processed = 0
    for file in files :
        row = {}
        instance = file.replace(".kh","").split('-')
        row["neg"] = instance[2]
        row["pos"] = instance[1]
        row["form"] = instance[0]
        instance_path = os.path.join(formulas_dir, file)
        print(f"Running: python kh_solver.py -f {instance_path}")
        row["time"] = ""
        row["result"] = ""
        try : 
            output = subprocess.run([sys.executable, "../../kh_solver.py", "-f", instance_path], timeout=30, capture_output=True).stdout.decode()
            lines = output.splitlines()
            for line in lines :
                if line.startswith("Time") :
                    row["time"] = line.split()[1]
                elif line.startswith("The formula") :
                    row["result"] = line.split()[3]
                elif line == "UNSAT" :
                    row["result"] = "UNSAT"
        except Exception as e:
            print(f'Error running: {instance_path}:'+str(e))
            row["time"] = "900"
            row["result"] = "TO"
        
        if row["time"] == "" or row["result"] == "":
            row["time"] = "ERR"
            row["result"] = "ERR"

        processed = processed + 1
        print(f"Progress: {round((processed/total_files) * 100,1)}%")
        result.append(row)

    fieldnames = ["form", "pos", "neg", "time", "result"]

    # Write to CSV
    csv_name = f"output-batch{i}.csv" if formulas_dir == "../formulas/" else f"output-interesting-batch{i}.csv"
    with open(csv_name, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()     # write header row
        writer.writerows(result)   # write data rows

if __name__ == "__main__" :
    parser = argparse.ArgumentParser(description="Process the formulas in batches.")

    parser.add_argument(
        "--dir",
        type=str,
        default="../formulas/",
        help="Path to the directory containing formulas (default: ../formulas/)"
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=10,
        help="The batch to be processed: 1,2,3,4,5"
    )

    parser.add_argument(
        "--all",
        type=bool,
        default=None,
        help="Option to process all the batches"
    )
    args = parser.parse_args()
    if  not args.all :
        print(f"Processing batch: {args.batch} from directory: {args.dir}")
        process_batch(args.batch, args.dir)
        csv_name = f"output-batch{args.batch}.csv" if args.dir == "../formulas/" else f"output-interesting-batch{args.batch}.csv"
        print(f"Result written in {csv_name}")
    else :
        for i in [1,2,3,4,5] :
            print(f"Processing all the formulas in batch {i} from directory: {args.dir}")
            process_batch(i, args.dir)

