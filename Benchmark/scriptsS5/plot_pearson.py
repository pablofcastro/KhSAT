import pandas as pd
import numpy as np
import glob
import sys
import os
from itertools import combinations
import matplotlib.pyplot as plt

# ===================================================================
# 1. CARGA Y LIMPIEZA DE DATOS
# ===================================================================
file_list = glob.glob("output-batch*.csv")
if os.path.exists("other_batchs"):
    file_list.extend(glob.glob("other_batchs/*.csv"))

if not file_list:
    print("Error: Don't find any CSV files to process. Please run the benchmark first.")
    sys.exit(1)

dfs = []
for f in file_list:
    try:
        df_temp = pd.read_csv(f)
        if not df_temp.empty: dfs.append(df_temp)
    except: pass

df = pd.concat(dfs, ignore_index=True)
df["result"] = df["result"].astype(str).str.replace(".", "", regex=False)

# Numeric columns
numeric_cols = ["n", "m", "ratio", "modal_ratio", "z3_time", "translation_time", "time", "worlds", "diamonds", "boxes", "size"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Limpieza estricta para no arruinar la matemática
df = df.dropna(subset=["z3_time", "translation_time", "time", "ratio"])
df = df[df["modal_ratio"] < 900] # Quitamos el 999.9 de cajas=0
df = df.replace([np.inf, -np.inf], np.nan).dropna()

# ===================================================================
# 2. FEATURE ENGINEERING (Creación de Interacciones de Pares)
# ===================================================================
base_features = ["m", "ratio", "modal_ratio", "worlds", "diamonds", "boxes", "size"]
targets = ["z3_time", "translation_time", "time"]

# Creamos un nuevo dataframe solo con lo que vamos a correlacionar
inter_df = df[targets + base_features].copy()

# Generamos las combinaciones multiplicativas (Variable 1 * Variable 2)
pares_creados = []
for v1, v2 in combinations(base_features, 2):
    nombre_par = f"{v1} X {v2}"
    inter_df[nombre_par] = inter_df[v1] * inter_df[v2]
    pares_creados.append(nombre_par)

# ===================================================================
# 3. CÁLCULO DE CORRELACIÓN DE PEARSON
# ===================================================================
# Calculamos la matriz de correlación completa
corr_matrix = inter_df.corr(method='pearson')

# Extraemos las correlaciones contra nuestros objetivos (aislando las variables independientes)
corr_z3 = corr_matrix["z3_time"].drop(targets).sort_values(ascending=False)
corr_trans = corr_matrix["translation_time"].drop(targets).sort_values(ascending=False)
corr_total = corr_matrix["time"].drop(targets).sort_values(ascending=False)

# ===================================================================
# 4. REPORTE EN CONSOLA
# ===================================================================
print("\n" + "="*70)
print("=== MINERÍA DE PARES: ¿QUÉ COMBINACIONES DISPARAN EL TIEMPO? ===")
print("="*70)

def imprimir_top(serie_corr, titulo, top_n=15):
    print(f"\n[ TOP {top_n} IMPACTOS EN {titulo} ]")
    print(f"{'Variable / Combinación (A x B)'.ljust(35)} | Correlación de Pearson")
    print("-" * 60)
    for index, value in serie_corr.head(top_n).items():
        # Marcamos con un asterisco las combinaciones para distinguirlas de las variables sueltas
        marca = "⭐" if " X " in index else "  "
        print(f"{marca} {index.ljust(32)} | {value:.4f}")

imprimir_top(corr_trans, "TIEMPO DE TRADUCCIÓN (Python)")
imprimir_top(corr_z3, "TIEMPO DE RESOLUCIÓN LÓGICA (Z3)")
imprimir_top(corr_total, "TIEMPO TOTAL (Python + Z3)")

print("\n(⭐ = Término de interacción / Combinación de dos variables)")

# ===================================================================
# 5. GRÁFICO DE BARRAS COMPARATIVO
# ===================================================================
# Tomamos el Top 15 combinado (sacando valores absolutos para ver la fuerza del impacto)
top_features_z3 = corr_z3.abs().sort_values(ascending=False).head(15).index
top_features_trans = corr_trans.abs().sort_values(ascending=False).head(15).index

# Unimos los tops sin duplicados para el gráfico
features_plot = list(dict.fromkeys(list(top_features_z3) + list(top_features_trans)))[:20]

valores_z3 = [corr_z3.get(f, 0) for f in features_plot]
valores_trans = [corr_trans.get(f, 0) for f in features_plot]

x = np.arange(len(features_plot))
width = 0.35

fig, ax = plt.subplots(figsize=(14, 8))
rects1 = ax.bar(x - width/2, valores_z3, width, label='Z3 Time', color='green', edgecolor='black')
rects2 = ax.bar(x + width/2, valores_trans, width, label='Translation Time (Python)', color='purple', edgecolor='black')

ax.set_ylabel('Correlación de Pearson (1.0 = Máximo impacto)')
ax.set_title('Impacto de Variables Simples y Pares Combinados sobre el Tiempo')
ax.set_xticks(x)
ax.set_xticklabels(features_plot, rotation=45, ha='right')
ax.legend()
ax.grid(True, axis='y', linestyle='--', alpha=0.6)

plt.axhline(0, color='black', linewidth=1)
plt.tight_layout()
plt.show()