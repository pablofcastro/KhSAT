import subprocess
import os
import csv
import argparse
import re
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def run_solver(instance_path, method):
    try:
        output_bytes = subprocess.run(
            [sys.executable, "../../kh_solver.py", "-f", instance_path, "-m", method], 
            timeout=300, 
            capture_output=True
        ).stdout
        output = output_bytes.decode('utf-8', errors='ignore')
        
        time_val = "300"
        result_val = "ERR"
        
        for line in output.splitlines():
            if line.startswith("Time"):
                time_val = line.split()[1]
            elif line.startswith("The formula"):
                result_val = line.split()[3].replace(".", "")
            elif line.strip() in ["SAT", "UNSAT"]:
                result_val = line.strip()
                
        return result_val, time_val
    except subprocess.TimeoutExpired:
        return "TO", "300"
    except Exception as e:
        print(f"Error running {instance_path} with method {method}: {e}")
        return "ERR", "300"

def process_batch(i, formulas_dir="../formulas/"):
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+).kh$")
    files = []
    
    if not os.path.exists(formulas_dir):
        print(f"Directory not found: {formulas_dir}")
        return
        
    for filename in os.listdir(formulas_dir):
        m = pattern.match(filename)
        if m:
            n = int(m.group(1))
            if n < i*10 and n >= (i-1)*10 :
                files.append(filename)
                
    result = [] # list of dicts, each dict is a row
    total_files = len(files)
    if total_files == 0:
        print(f"No files found for batch {i} in directory {formulas_dir}")
        return
        
    print(f"Running comparison for batch {i} ({total_files} files)")
    processed = 0
    
    for file in files:
        row = {}
        instance = file.replace(".kh","").split('-')
        row["form"] = instance[0]
        row["pos"] = instance[1]
        row["neg"] = instance[2]
        
        instance_path = os.path.join(formulas_dir, file)
        print(f"Running: python kh_solver.py -f {instance_path}")
        
        # Corremos para NEW
        res_new, time_new_str = run_solver(instance_path, "new")
        # Corremos para OLD
        res_old, time_old_str = run_solver(instance_path, "old")
        
        row["time_new"] = time_new_str
        row["result_new"] = res_new
        row["time_old"] = time_old_str
        row["result_old"] = res_old
        
        # Determinar cual fue mas rapido
        try:
            t_new = float(time_new_str)
        except:
            t_new = 300.0
            
        try:
            t_old = float(time_old_str)
        except:
            t_old = 300.0
            
        if t_new < t_old:
            row["fastest"] = "new"
        elif t_old < t_new:
            row["fastest"] = "old"
        else:
            row["fastest"] = "tie"
            
        processed += 1
        print(f"Progress: {round((processed/total_files) * 100, 1)}%")
        result.append(row)
        
    if not result:
        return
        
    fieldnames = result[0].keys()
    
    csv_file = f"comparison_batch_{i}.csv" if formulas_dir == "../formulas/" else f"comparison_interesting_batch_{i}.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result)
        
    print(f"Comparison results saved to {csv_file}")
    
    plot_results(result, i, formulas_dir)

def plot_results(data, batch_ind, formulas_dir="../formulas/"):
    df = pd.DataFrame(data)
    
    # Contamos cuantas instancias cayeron en cada categoria
    counts_new = df['result_new'].value_counts()
    counts_old = df['result_old'].value_counts()
    
    categories = ['SAT', 'UNSAT', 'TO', 'ERR']
    new_data = [counts_new.get(c, 0) for c in categories]
    old_data = [counts_old.get(c, 0) for c in categories]
    
    # Graficar resultados (barras)
    fig, ax1 = plt.subplots(figsize=(8, 6))
    
    width = 0.35
    x = np.arange(len(categories))
    
    rects1 = ax1.bar(x - width/2, new_data, width, label='new', color='skyblue')
    rects2 = ax1.bar(x + width/2, old_data, width, label='old', color='salmon')
    
    ax1.set_ylabel('Number of Instances')
    ax1.set_title(f'Result Comparison (Batch {batch_ind})')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.legend()
    
    for rect in rects1 + rects2:
        height = rect.get_height()
        if height > 0:
            ax1.annotate(f'{height}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), 
                        textcoords="offset points",
                        ha='center', va='bottom')

    plt.tight_layout()
    plot_name = f"comparison_plot_batch_{batch_ind}.png" if formulas_dir == "../formulas/" else f"comparison_plot_interesting_batch_{batch_ind}.png"
    plt.savefig(plot_name)
    print(f"Plot saved as {plot_name}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process the formulas in batches and compare methods.")
    parser.add_argument(
        "--dir",
        type=str,
        default="../formulas/",
        help="Path to the directory containing formulas (default: ../formulas/)"
    )
    parser.add_argument("--batch", type=int, default=10, help="The batch to be processed: 1, 2, 3...")
    parser.add_argument("--all", action='store_true', help="Option to process all the batches")
    
    args = parser.parse_args()
    if not args.all:
        print(f"Processing batch: {args.batch} from directory: {args.dir}")
        process_batch(args.batch, args.dir)
    else:
        for i in [1,2,3,4,5]:
            print(f"Processing batch {i} from directory: {args.dir}")
            process_batch(i, args.dir)

