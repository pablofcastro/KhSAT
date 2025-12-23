import subprocess
import os
import csv
import argparse
import re

def process_batch(i) :
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+).kh$")
    files = []
    size = 0
    for filename in os.listdir(f"../formulas/"):
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
        instance = file.replace(".kh","").split('-')
        row["neg"] = instance[2]
        row["pos"] = instance[1]
        row["form"] = instance[0]
        instance_path = os.path.join(f"../formulas/", file)
        print(f"Running: python kh_solver.py -f {instance_path}")
        try : 
            output = subprocess.run(["python3", "../../kh_solver.py", "-f", instance_path], timeout=900, capture_output=True).stdout.decode()
            lines = output.splitlines()
            for line in lines :
                if line.startswith("Time") :
                    row["time"] = line.split()[1]
                elif line.startswith("The formula") :
                    row["result"] = line.split()[3]
        except Exception as e:
            print(f'Error running: {instance_path}:'+str(e))
            row["time"] = "900"
            row["result"] = "TO"
        processed = processed + 1
        print(f"Progress: {round((processed/total_files) * 100,1)}%")
        result.append(row)

    fieldnames = result[0].keys()

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
        type=bool,
        default=None,
        help="Option to process all the batches"
    )
    args = parser.parse_args()
    if  not args.all :
        print(f"Processing batch: {args.batch}")
        process_batch(args.batch)
        print(f"Result written in output-batch{args.batch}.csv")
    else :
        for i in [1,2,3,4,5] :
            print("Processing all the formulas")
            process_batch(i)

