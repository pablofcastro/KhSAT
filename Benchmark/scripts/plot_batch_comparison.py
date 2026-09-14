import argparse
import csv
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def generate_plots(batch_ind):
    graphs_dir = Path("graphs")
    
    csv_inc = graphs_dir / f"cnf_formulas_batch_{batch_ind}_incremental.csv"    #aca cambiar
    csv_basic = graphs_dir / f"cnf_formulas_batch_{batch_ind}_basic_opt.csv"

    if not csv_inc.exists() or not csv_basic.exists():
        print(f"Error: No se encontraron los archivos necesarios en '{graphs_dir}/'.")
        print(f"  - {csv_inc.name} ({'Encontrado' if csv_inc.exists() else 'FALTANTE'})")
        print(f"  - {csv_basic.name} ({'Encontrado' if csv_basic.exists() else 'FALTANTE'})")
        return

    # Cargar datasets
    df_inc = pd.read_csv(csv_inc)
    df_basic = pd.read_csv(csv_basic)

    # Crear una clave única (form_id) combinando form, pos y neg
    df_inc['form_id'] = df_inc['form'].astype(str) + '-' + df_inc['pos'].astype(str) + '-' + df_inc['neg'].astype(str)
    df_basic['form_id'] = df_basic['form'].astype(str) + '-' + df_basic['pos'].astype(str) + '-' + df_basic['neg'].astype(str)

    # Renombrar columnas de tiempo y resultado
    df_inc = df_inc.rename(columns={'time': 'time_incremental', 'result': 'result_incremental'})
    df_basic = df_basic.rename(columns={'time': 'time_basic_opt', 'result': 'result_basic_opt'})

    # Hacer el cruce (merge) usando la clave única 'form_id'
    df = pd.merge(
        df_inc[['form_id', 'pos', 'neg', 'time_incremental', 'result_incremental']],
        df_basic[['form_id', 'time_basic_opt', 'result_basic_opt']],
        on='form_id'
    )

    df['t_basic_opt'] = df['time_basic_opt'].astype(float)
    df['t_incremental'] = df['time_incremental'].astype(float)

    total_formulas = len(df)

    # 1. Gráfico de Torta (Speedup Categorización 2x)
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

    labels, sizes, colors = [], [], []
    for cat in category_order:
        count = pie_counts.get(cat, 0)
        if count > 0:
            labels.append(cat)
            sizes.append(count)
            colors.append(color_map[cat])

    fig_pie, ax_pie = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax_pie.pie(
        sizes, labels=labels, colors=colors, autopct='%1.1f%%',
        startangle=140, textprops=dict(color="black", size=10)
    )
    plt.setp(autotexts, size=10, weight="bold")
    ax_pie.set_title(f'Relative Performance - 2x Rule (Batch {batch_ind})\nTotal: {total_formulas} formulas', fontsize=12)
    plt.tight_layout()

    pie_plot_name = graphs_dir / f"pie_cnf_formulas_{batch_ind}.png"    #aca cambiar
    plt.savefig(pie_plot_name, dpi=300)
    plt.close(fig_pie)
    print(f"[OK] Pie chart guardado en: {pie_plot_name} (Total procesadas: {total_formulas})")

    # 2. Gráfico de Barras (Comparativo SAT / UNSAT / TO / ERR)
    categories = ['SAT', 'UNSAT', 'TO', 'ERR']
    counts_basic_opt = df['result_basic_opt'].value_counts()
    counts_incremental = df['result_incremental'].value_counts()

    basic_opt_data = [counts_basic_opt.get(c, 0) for c in categories]
    incremental_data = [counts_incremental.get(c, 0) for c in categories]

    fig1, ax1 = plt.subplots(figsize=(8, 6))
    width = 0.35
    x = np.arange(len(categories))

    rects1 = ax1.bar(x - width/2, basic_opt_data, width, label='basic_opt', color='#85aae4')
    rects2 = ax1.bar(x + width/2, incremental_data, width, label='incremental', color="#fe7c8a")

    ax1.set_ylabel('Number of Instances')
    ax1.set_title(f'Result Comparison (Batch {batch_ind} - {total_formulas} formulas)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.legend()

    for rect in rects1 + rects2:
        height = rect.get_height()
        if height > 0:
            ax1.annotate(f'{height}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom')

    plt.tight_layout()
    plot_name = graphs_dir / f"comparison_cnf_formulas_batch_{batch_ind}.png"   #aca cambiar
    plt.savefig(plot_name, dpi=300)
    plt.close(fig1)
    print(f"[OK] Comparison plot guardado en: {plot_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera gráficos comparativos leyendo los CSVs de incremental y basic-opt.")
    parser.add_argument("--batch", type=int, default=1, help="Número de batch a graficar (default: 1)")
    parser.add_argument("--all", action='store_true', help="Opción para graficar todos los batches (1 al 5)")

    args = parser.parse_args()
    batches = [1, 2, 3, 4, 5] if args.all else [args.batch]

    for b in batches:
        print(f"\n================ Graficando Batch {b} ================")
        generate_plots(b)