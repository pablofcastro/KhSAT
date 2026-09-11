import subprocess
import os
import csv
import argparse
import re
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Determina la carpeta donde está ESTE script (scripts/) y apunta a scripts/graphs
SCRIPT_DIR = Path(__file__).resolve().parent
GRAPHS_DIR = SCRIPT_DIR / "graphs"

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
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+)_leaf_\d+\.csv$")
    files = []
    
    if not os.path.exists(formulas_dir):
        print(f"Directory not found: {formulas_dir}")
        return
        
    for filename in os.listdir(formulas_dir):
        m = pattern.match(filename)
        if m:
            n = int(m.group(1))
            if n < i*10 and n >= (i-1)*10:
                files.append(filename)
                
    result = []
    total_files = len(files)
    if total_files == 0:
        print(f"No files found for batch {i} in directory {formulas_dir}")
        return
        
    print(f"Running comparison for batch {i} ({total_files} files)")
    processed = 0
    
    for file in files:
        row = {}
        m = pattern.match(file)
        if m:
            row["form"] = f"formula{m.group(1)}"
            row["pos"] = m.group(2)
            row["neg"] = m.group(3)
        
        instance_path = os.path.join(formulas_dir, file)
        print(f"Running: python kh_solver.py -f {instance_path}")
        
        res_basic_opt, time_basic_opt_str = run_solver(instance_path, "basic-opt")
        res_incremental, time_incremental_str = run_solver(instance_path, "incremental")
        
        row["time_basic_opt"] = time_basic_opt_str
        row["result_basic_opt"] = res_basic_opt
        row["time_incremental"] = time_incremental_str
        row["result_incremental"] = res_incremental
        
        try:
            t_basic_opt = float(time_basic_opt_str)
        except:
            t_basic_opt = 300.0
            
        try:
            t_incremental = float(time_incremental_str)
        except:
            t_incremental = 300.0
            
        if t_basic_opt < t_incremental:
            row["fastest"] = "basic_opt"
        elif t_incremental < t_basic_opt:
            row["fastest"] = "incremental"
        else:
            row["fastest"] = "tie"
            
        processed += 1
        print(f"Progress: {round((processed/total_files) * 100, 1)}%")
        result.append(row)
        
    if not result:
        return
        
    fieldnames = result[0].keys()
    
    # Garantiza la existencia de bBenchmark/scripts/graphs
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    
    csv_file = GRAPHS_DIR / f"comparison_tree_batch_{i}.csv"
    
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result)
        
    print(f"Comparison results saved to {csv_file}")
    
    plot_results(result, i, formulas_dir)

def plot_results(data, batch_ind, formulas_dir="../formulas/"):
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(data)
    
    df['t_basic_opt'] = df['time_basic_opt'].astype(float)
    df['t_incremental'] = df['time_incremental'].astype(float)
    
    def classify_speedup(row):
        t_n = row['t_basic_opt']
        t_p = row['t_incremental']
        
        if t_n == t_p:
            return "Tie (difference < 2x)"
        elif t_p >= 2 * t_n:
            return "basic_opt (at least 2x faster)"
        elif t_n >= 2 * t_p:
            return "incremental (at least 2x faster)"
        else:
            return "Tie (difference < 2x)"

    df['speedup_category'] = df.apply(classify_speedup, axis=1)
    
    pie_counts = df['speedup_category'].value_counts()
    
    category_order = [
        "basic_opt (at least 2x faster)", 
        "incremental (at least 2x faster)", 
        "Tie (difference < 2x)"
    ]
    color_map = {
        "basic_opt (at least 2x faster)": "#85aae4",
        "incremental (at least 2x faster)": "#fe7c8a",
        "Tie (difference < 2x)": "#c1de6e"
    }
    
    labels = []
    sizes = []
    colors = []
    
    for cat in category_order:
        count = pie_counts.get(cat, 0)
        if count > 0:
            labels.append(cat)
            sizes.append(count)
            colors.append(color_map[cat])

    fig_pie, ax_pie = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax_pie.pie(
        sizes, 
        labels=labels, 
        colors=colors, 
        autopct='%1.1f%%',
        startangle=140,
        textprops=dict(color="black", size=10)
    )
    plt.setp(autotexts, size=10, weight="bold")
    ax_pie.set_title(f'Relative Performance - 2x Rule (Batch {batch_ind})\nTotal: {len(df)} formulas', fontsize=12)
    
    plt.tight_layout()
    pie_plot_name = GRAPHS_DIR / f"pie_speedup_tree_batch_{batch_ind}.png"
    plt.savefig(pie_plot_name, dpi=300)
    plt.close(fig_pie)
    print(f"Pie chart saved as {pie_plot_name}")

    counts_basic_opt = df['result_basic_opt'].value_counts()
    counts_incremental = df['result_incremental'].value_counts()
    
    categories = ['SAT', 'UNSAT', 'TO', 'ERR']
    basic_opt_data = [counts_basic_opt.get(c, 0) for c in categories]
    incremental_data = [counts_incremental.get(c, 0) for c in categories]
    
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    width = 0.35
    x = np.arange(len(categories))
    
    rects1 = ax1.bar(x - width/2, basic_opt_data, width, label='basic_opt', color='#85aae4')
    rects2 = ax1.bar(x + width/2, incremental_data, width, label='incremental', color="#fe7c8a")
    
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
    plot_name = GRAPHS_DIR / f"comparison_tree_batch_{batch_ind}.png"
    plt.savefig(plot_name, dpi=300)
    plt.close(fig1)
    print(f"Plot saved as {plot_name}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process the formulas in batches and compare methods.")
    parser.add_argument(
        "--dir",
        type=str,
        default="../formulas/",
        help="Path to the directory containing formulas (default: ../formulas/)"
    )
    parser.add_argument("--batch", type=int, default=1, help="The batch to be processed: 1, 2, 3...")
    parser.add_argument("--all", action='store_true', help="Option to process all the batches")
    
    args = parser.parse_args()
    if not args.all:
        print(f"Processing batch: {args.batch} from directory: {args.dir}")
        process_batch(args.batch, args.dir)
    else:
        for i in [1, 2, 3, 4, 5]:
            print(f"Processing batch {i} from directory: {args.dir}")
            process_batch(i, args.dir)