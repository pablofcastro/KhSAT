import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
import glob
import argparse

# ===================================================================
# 0. CONFIGURACIÓN DE PARÁMETROS Y FLAGS DE LÍNEA DE COMANDOS
# ===================================================================
parser = argparse.ArgumentParser(description="Generador de gráficos de transición de fase S5.")
parser.add_argument("--all", "-a", action="store_true", 
                    help="Incluir también todos los CSVs almacenados en la carpeta 'other_batchs/'.")
args = parser.parse_args()

# ===================================================================
# 1. CARGA Y LIMPIEZA DE DATOS
# ===================================================================
# Busca automáticamente todos los output-batch*.csv en la carpeta actual
file_list = glob.glob("output-batch*.csv")

# Si se pasa el flag --all, agregamos los CSVs de la carpeta 'other_batchs/'
if args.all:
    other_folder = "other_batchs"
    if os.path.exists(other_folder):
        other_files = glob.glob(os.path.join(other_folder, "*.csv"))
        file_list.extend(other_files)
        print(f"--> MODO COMPLETO (--all) ACTIVADO: Procesando {len(file_list)} CSVs (actuales + '{other_folder}/').")
    else:
        print(f"--> ADVERTENCIA: Se usó --all pero la carpeta '{other_folder}/' no existe aún. Procesando solo actuales.")
else:
    print(f"--> MODO SOLO ACTUALES ACTIVADO: Procesando {len(file_list)} CSVs de la carpeta actual.")
    print("    (Tip: Usa 'python3 plot_modal.py --all' para incluir los de 'other_batchs/')")

dfs = []
for f in file_list:
    try:
        df_temp = pd.read_csv(f)
        if not df_temp.empty:
            dfs.append(df_temp)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        pass

if not dfs:
    print("No se encontraron archivos CSV válidos con datos. Verifica la carpeta.")
    sys.exit(1)
    
df = pd.concat(dfs, ignore_index=True)
df["result"] = df["result"].str.replace(".", "", regex=False)

# Aseguramos tipos numéricos
numeric_cols = ["n", "ratio", "time", "worlds", "diamonds", "boxes"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Auto-detectar 'n'
df = df.dropna(subset=["n"])
df["n"] = df["n"].astype(int)
n_values = sorted(df["n"].unique())
print(f"Valores de 'n' detectados: {n_values}")

# Calcular Relación Modal (Diamantes / Cajas)
if "diamonds" in df.columns and "boxes" in df.columns:
    df["diam_box_ratio"] = df["diamonds"] / df["boxes"].replace(0, np.nan)
    # Agrupamos en los saltos (0.5, 1.0, 1.5, 2.0, etc.)
    df["rm_group"] = df["diam_box_ratio"].round(1)

# Estilos unificados
COLORS = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple", "tab:brown"]
LINESTYLES = ["-", "--", ":", "-."]
MARKERS = ["o", "s", "^", "D", "v", "P"]

def style_for(idx):
    return {"color": COLORS[idx % len(COLORS)], "linestyle": LINESTYLES[idx % len(LINESTYLES)], "marker": MARKERS[idx % len(MARKERS)]}

# ===================================================================
# FUNCIÓN DE INTERPOLACIÓN DEL THRESHOLD
# ===================================================================
def interpolate_threshold(frac):
    xs = frac.index.to_numpy()
    ys = frac.values
    if 0.5 in ys:
        return xs[list(ys).index(0.5)]
    for i in range(len(xs) - 1):
        if (ys[i] >= 0.5 and ys[i + 1] <= 0.5):
            t = (0.5 - ys[i]) / (ys[i + 1] - ys[i])
            return xs[i] + t * (xs[i + 1] - xs[i])
    return None

# Pre-calculamos Thresholds
thresholds_rm = {}
n_target = max(n_values)
n_df = df[df["n"] == n_target].copy()
decided = n_df[n_df["result"] != "TO"]
rm_groups = sorted(decided["rm_group"].dropna().unique())

for rm in rm_groups:
    sub_df = decided[decided["rm_group"] == rm]
    frac = sub_df.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index()
    if len(frac) > 1:
        thresholds_rm[rm] = interpolate_threshold(frac)

# ===================================================================
# T1: LA SIGMOIDE - TRANSICIÓN DE FASE SEPARADA POR RELACIÓN MODAL
# ===================================================================
plt.figure(figsize=(10, 6))
plt.axhline(0.5, color="black", linestyle="--", linewidth=1.5, label="Cruce P(SAT) = 0.5")

for idx, rm in enumerate(rm_groups):
    st = style_for(idx)
    sub_df = decided[decided["rm_group"] == rm]
    frac = sub_df.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index()
    
    if len(frac) > 1:
        plt.plot(frac.index, frac.values, marker=st["marker"], linestyle=st["linestyle"],
                 color=st["color"], label=f"Diam/Cajas = {rm}")
        th = thresholds_rm.get(rm)
        if th is not None:
            plt.axvline(th, color=st["color"], linestyle=":", linewidth=2, alpha=0.8)

plt.xlabel("Densidad Proposicional (Ratio M/N)")
plt.ylabel("Probabilidad de ser SAT (P(SAT))")
plt.ylim(-0.05, 1.05)
plt.title(f"T1: Curvas Sigmoides de Transición de Fase (n={n_target})\n"
          "Líneas punteadas verticales marcan el Threshold exacto P(SAT)=0.5.")
plt.legend()
plt.grid(True, alpha=0.3)

# ===================================================================
# T2: CAMPANA DE DIFICULTAD SEPARADA POR RELACIÓN MODAL
# ===================================================================
plt.figure(figsize=(10, 6))
for idx, rm in enumerate(rm_groups):
    st = style_for(idx)
    sub_df = decided[decided["rm_group"] == rm]
    med = sub_df.groupby("ratio")["time"].median().sort_index()
    
    if len(med) > 1:
        plt.plot(med.index, med.values, marker=st["marker"], linestyle=st["linestyle"],
                 color=st["color"], label=f"Diam/Cajas = {rm}")
        th = thresholds_rm.get(rm)
        if th is not None:
            plt.axvline(th, color=st["color"], linestyle=":", linewidth=2, alpha=0.8)

plt.xlabel("Densidad Proposicional (Ratio M/N)")
plt.ylabel("Tiempo Mediano (s)")
plt.yscale("log")
plt.title(f"T2: Dificultad Computacional y Thresholds (n={n_target})\n"
          "Alineación visual del pico de la campana con el Threshold P(SAT)=0.5.")
plt.legend()
plt.grid(True, alpha=0.3)

# ===================================================================
# T3: DIFICULTAD AISLANDO LA CANTIDAD DE MUNDOS FÍSICOS (Cada 100)
# ===================================================================
plt.figure(figsize=(11, 6))

decided_w = decided.copy()
max_worlds = int(decided_w["worlds"].max()) if not decided_w.empty else 1600
bins = list(range(0, max_worlds + 200, 100))
labels = [f"{bins[i]}-{bins[i+1]}" for i in range(len(bins)-1)]
decided_w["w_bucket"] = pd.cut(decided_w["worlds"], bins=bins, labels=labels)

active_buckets = sorted(decided_w["w_bucket"].dropna().unique(), key=lambda x: labels.index(x))

for idx, bucket in enumerate(active_buckets):
    st = style_for(idx)
    sub_df = decided_w[decided_w["w_bucket"] == bucket]
    med = sub_df.groupby("ratio")["time"].median().sort_index()
    frac = sub_df.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index()
    
    if len(med) > 1:
        plt.plot(med.index, med.values, marker=st["marker"], linestyle="-", linewidth=2,
                 color=st["color"], label=str(bucket))
        th = interpolate_threshold(frac)
        if th is not None:
            plt.axvline(th, color=st["color"], linestyle=":", linewidth=2, alpha=0.8)

plt.xlabel("Densidad Proposicional (Ratio M/N)")
plt.ylabel("Tiempo Mediano (s)")
plt.yscale("log")
plt.title(f"T3: Campanas y Thresholds por Tamaño del Modelo (n={n_target})\n"
          "Cada grupo de mundos muestra su línea de Threshold individual.")
plt.legend(title="Mundos Reales", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, alpha=0.3)
plt.tight_layout()

# ===================================================================
# T4: MAPA DE CALOR (HEATMAP) 2D - RATIO vs RELACIÓN MODAL
# ===================================================================
plt.figure(figsize=(10, 8))
pivot = decided.pivot_table(index="rm_group", columns="ratio", values="time", aggfunc="median")

if not pivot.empty:
    plt.imshow(pivot.values, aspect="auto", origin="lower", cmap="viridis",
               extent=[pivot.columns.min(), pivot.columns.max(), pivot.index.min(), pivot.index.max()])
    plt.colorbar(label="Tiempo Mediano de Ejecución (s)")
    plt.xlabel("Densidad Proposicional (Ratio M/N)")
    plt.ylabel("Relación Modal (Diamantes / Cajas)")
    plt.title(f"T4: Heatmap de Complejidad S5 (n={n_target})\n"
              "Vista superior de la zona de asfixia del solver Z3.")
else:
    print("Warning: No hay datos suficientes para el Heatmap T4.")

# ===================================================================
# T5: LA MONTAÑA 3D (LÍNEAS) - RATIO vs RELACIÓN MODAL vs TIEMPO
# ===================================================================
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')

max_time_global = decided["time"].max()
cmap = plt.get_cmap('coolwarm')

for rm_val in rm_groups:
    sub_df = decided[decided["rm_group"] == rm_val]
    grouped = sub_df.groupby("ratio")["time"].median().sort_index()
    
    if len(grouped) > 1:
        xs = grouped.index.to_numpy()
        zs = grouped.values
        ys = np.full_like(xs, rm_val)
        
        color_val = cmap(zs.max() / max_time_global)
        ax.plot(xs, ys, zs, color=color_val, linewidth=3, alpha=0.8)
        ax.scatter(xs, ys, zs, color=color_val, s=25, edgecolors='white', linewidth=0.5)

ax.set_xlabel('Ratio M/N', labelpad=10)
ax.set_ylabel('Diamantes / Cajas', labelpad=10)
ax.set_zlabel('Tiempo Mediano (s)', labelpad=10)
ax.set_title(f"T5: Topología de la Dificultad Modal S5 (n={n_target})\n"
             "Líneas de nivel que muestran la explosión de tiempo.")
ax.view_init(elev=25, azim=135)
plt.tight_layout()

# ===================================================================
# ANÁLISIS ESTADÍSTICO DE LOS DATOS (Consola)
# ===================================================================
print("\n" + "="*60)
print("=== RESUMEN DE LA ANATOMÍA DE FÓRMULAS DIFÍCILES ===")
print("="*60)

for n in n_values:
    n_df = df[(df["n"] == n) & (df["result"] != "TO")].copy()
    if n_df.empty: continue
    
    print(f"\n--- Resultados para n = {n} ---")
    
    grouped = n_df.groupby("ratio").agg(
        median_time=("time", "median"), avg_boxes=("boxes", "mean"), avg_diamonds=("diamonds", "mean")
    ).reset_index()
    
    peak = grouped.loc[grouped["median_time"].idxmax()]
    print("1. PICO CENTRAL (Mediana de la muestra general):")
    print(f"   - Ratio Crítico: {peak['ratio']:.2f}  |  Tiempo: {peak['median_time']:.4f} s")
    print(f"   - Diamantes: {peak['avg_diamonds']:.0f}  |  Cajas: {peak['avg_boxes']:.0f}")

    top_percent = 0.05
    k_top = max(1, int(len(n_df) * top_percent))
    top_formulas = n_df.nlargest(k_top, "time")
    
    print(f"\n2. CASOS PATOLÓGICOS (Top {int(top_percent*100)}% fórmulas más lentas):")
    print(f"   - Ratio Promedio: {top_formulas['ratio'].mean():.2f}")
    print(f"   - Diamantes Promedio: {top_formulas['diamonds'].mean():.0f}")
    print(f"   - Cajas Promedio: {top_formulas['boxes'].mean():.0f}")
    print(f"   - Relación Modal (Diam/Cajas) Promedio: {top_formulas['diam_box_ratio'].mean():.2f}")

print("\n" + "="*60)

# ===================================================================
# T6: LA ECUACIÓN DE LA DIFICULTAD S5 (Mundos vs Threshold)
# ===================================================================
plt.figure(figsize=(10, 6))

x_worlds = []
y_thresholds = []

# Reutilizamos los buckets de mundos calculados en T3
for bucket in active_buckets:
    sub_df = decided_w[decided_w["w_bucket"] == bucket]
    if sub_df.empty: 
        continue
    
    # Buscamos el threshold para este grupo de mundos
    frac = sub_df.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index()
    th = interpolate_threshold(frac)
    
    if th is not None:
        # Tomamos la cantidad real de mundos promedio en este bucket como coordenada X
        mean_w = sub_df["worlds"].mean()
        x_worlds.append(mean_w)
        y_thresholds.append(th)

if len(x_worlds) > 1:
    # 1. Dibujamos los puntos reales
    plt.scatter(x_worlds, y_thresholds, color="red", s=100, zorder=5, edgecolors='black', label="Thresholds Empíricos")
    
    # 2. Calculamos la Regresión Lineal (Y = mX + B)
    # x_worlds = Mundos, y_thresholds = Ratio
    coefs, cov = np.polyfit(x_worlds, y_thresholds, 1, cov=True)
    m, b = coefs # m = pendiente, b = ordenada al origen
    
    # R-cuadrado para ver qué tan perfecto es el ajuste
    correlation_matrix = np.corrcoef(x_worlds, y_thresholds)
    correlation_xy = correlation_matrix[0,1]
    r_squared = correlation_xy**2
    
    # 3. Dibujamos la recta de tendencia
    x_line = np.linspace(min(x_worlds)*0.8, max(x_worlds)*1.1, 100)
    y_line = m * x_line + b
    
    plt.plot(x_line, y_line, color="blue", linestyle="--", linewidth=2,
             label=f"Ajuste Lineal ($R^2={r_squared:.2f}$)\n$Ratio = {m:.4f} \\times W + {b:.2f}$")
    
    # Imprimimos tu descubrimiento por consola
    print("\n" + "*"*70)
    print("🌟 ¡DESCUBRIMIENTO: LA ECUACIÓN DE TRANSICIÓN DE FASE S5! 🌟")
    print("*"*70)
    print(f"Para N={n_target}, la relación matemática entre Mundos (W) y Ratio Crítico (r) es:")
    print(f"   --->  r = {m:.4f} * W + {b:.4f}")
    print(f"Precisión del ajuste (R^2): {r_squared:.4f} (1.0 es perfecto)")
    print("*"*70 + "\n")
else:
    print("\nNota: Se necesitan al menos 2 Thresholds válidos para calcular la regresión lineal en T6.")

plt.xlabel("Cantidad Promedio de Mundos ($W$)")
plt.ylabel("Ratio Crítico (Umbral $P(SAT) = 0.5$)")
plt.title(f"T6: Relación Matemática entre Mundos y Transición de Fase (n={n_target})\n"
          "Comprobación empírica del desplazamiento del Threshold computacional en S5.")
plt.legend()
plt.grid(True, linestyle=":", alpha=0.6)

# Mostrar las ventanas de los gráficos
plt.show()