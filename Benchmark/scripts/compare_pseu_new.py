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
        # Corremos para pseu
        res_pseu, time_pseu_str = run_solver(instance_path, "pseu")
        
        row["time_new"] = time_new_str
        row["result_new"] = res_new
        row["time_pseu"] = time_pseu_str
        row["result_pseu"] = res_pseu
        
        # Determinar cual fue mas rapido
        try:
            t_new = float(time_new_str)
        except:
            t_new = 300.0
            
        try:
            t_pseu = float(time_pseu_str)
        except:
            t_pseu = 300.0
            
        if t_new < t_pseu:
            row["fastest"] = "new"
        elif t_pseu < t_new:
            row["fastest"] = "pseu"
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
    
    # Convertir los tiempos a flotantes para operar
    df['t_new'] = df['time_new'].astype(float)
    df['t_pseu'] = df['time_pseu'].astype(float)
    
    # -------------------------------------------------------------
    # 1. Lógica para el Gráfico de Torta (Regla del 2x)
    # -------------------------------------------------------------
    def classify_speedup(row):
        t_n = row['t_new']
        t_p = row['t_pseu']
        
        # Evitar división por cero o casos de timeout igualados
        if t_n == t_p:
            return "Empate (diferencia < 2x)"
        elif t_p >= 2 * t_n:
            return "new (al menos 2x más rápido)"
        elif t_n >= 2 * t_p:
            return "pseu (al menos 2x más rápido)"
        else:
            return "Empate (diferencia < 2x)"

    df['speedup_category'] = df.apply(classify_speedup, axis=1)
    
    # Conteo de casos para la torta
    pie_counts = df['speedup_category'].value_counts()
    
    # Definir orden y colores fijos para coherencia visual
    category_order = [
        "new (al menos 2x más rápido)", 
        "pseu (al menos 2x más rápido)", 
        "Empate (diferencia < 2x)"
    ]
    color_map = {
        "new (al menos 2x más rápido)": "#2ca02c",  # Verde
        "pseu (al menos 2x más rápido)": "#1f77b4", # Azul
        "Empate (diferencia < 2x)": "#d62728"       # Gris/Rojo suave
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

    # Graficar Torta
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
    ax_pie.set_title(f'Rendimiento Relativo - Regla 2x (Batch {batch_ind})\nTotal: {len(df)} fórmulas', fontsize=12)
    
    plt.tight_layout()
    pie_plot_name = f"pie_speedup_batch_{batch_ind}.png" if formulas_dir == "../formulas/" else f"pie_speedup_interesting_batch_{batch_ind}.png"
    plt.savefig(pie_plot_name, dpi=300)
    plt.close(fig_pie)
    print(f"Pie chart saved as {pie_plot_name}")

    # -------------------------------------------------------------
    # 2. Gráfico de Barras Original (SAT, UNSAT, TO, ERR)
    # -------------------------------------------------------------
    counts_new = df['result_new'].value_counts()
    counts_pseu = df['result_pseu'].value_counts()
    
    categories = ['SAT', 'UNSAT', 'TO', 'ERR']
    new_data = [counts_new.get(c, 0) for c in categories]
    pseu_data = [counts_pseu.get(c, 0) for c in categories]
    
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    width = 0.35
    x = np.arange(len(categories))
    
    rects1 = ax1.bar(x - width/2, new_data, width, label='new', color='skyblue')
    rects2 = ax1.bar(x + width/2, pseu_data, width, label='pseu', color='salmon')
    
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

