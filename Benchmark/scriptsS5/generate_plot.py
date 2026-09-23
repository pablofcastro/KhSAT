import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys

# ---- Load multiple CSV files ----
file_list = ["output-batch1.csv", "output-batch2.csv", "output-batch3.csv", "output-batch4.csv", "output-batch5.csv"]

dfs = []
for f in file_list:
    try:
        dfs.append(pd.read_csv(f))
    except (pd.errors.EmptyDataError, FileNotFoundError):
        print(f"Skipping {f}: empty or missing")

if not dfs:
    print("No CSV files with data found. Run run_benchmark.py first.")
    sys.exit(1)
df = pd.concat(dfs, ignore_index=True)

# ---- Clean result column (e.g., 'SAT.' -> 'SAT') ----
df["result"] = df["result"].str.replace(".", "", regex=False)

# ---- Auto-detect the distinct values of n present in the data ----
df["n"] = df["n"].astype(int)
n_values = sorted(df["n"].unique())
print(f"Detected n values: {n_values}")

# ---- Normalized time per formula size (G7) ----
if "size" in df.columns:
    df["time_per_size"] = df["time"] / df["size"]
else:
    print("Warning: 'size' column not found in the CSVs. G7 (normalized time) will be skipped. "
          "Regenerate the benchmarks with run_benchmark.py to include it.")

# ---- Per-n style mapping (color + linestyle + marker) ----
COLORS = ["tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple", "tab:brown"]
LINESTYLES = ["-", "--", ":", "-."]
MARKERS = ["o", "s", "^", "D", "v", "P"]


def style_for(idx):
    return {
        "color": COLORS[idx % len(COLORS)],
        "linestyle": LINESTYLES[idx % len(LINESTYLES)],
        "marker": MARKERS[idx % len(MARKERS)],
    }


def interpolate_threshold(frac):
    xs = frac.index.to_numpy()
    ys = frac.values
    for i in range(len(xs) - 1):
        if ys[i] >= 0.5 > ys[i + 1]:
            t = (0.5 - ys[i]) / (ys[i + 1] - ys[i])
            return xs[i] + t * (xs[i + 1] - xs[i])
    return None

# ===================================================================
# G1: Phase transition curve (probability of satisfiability)
# ===================================================================
plt.figure()
plt.axhline(0.5, color="red", linestyle="--", linewidth=1, label="P(SAT) = 0.5")
for idx, n in enumerate(n_values):
    st = style_for(idx)
    n_df = df[df["n"] == n]
    decided = n_df[n_df["result"] != "TO"]
    frac = decided.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean())
    frac = frac.sort_index()
    threshold = interpolate_threshold(frac)
    print(f"Interpolated critical threshold (P(SAT)=0.5) for n={n}: ratio = {threshold}")
    plt.plot(frac.index, frac.values, marker=st["marker"], linestyle=st["linestyle"],
             color=st["color"], label=f"P(SAT) n={n}")
    if threshold is not None:
        plt.axvline(threshold, color=st["color"], linestyle=":", linewidth=1, alpha=0.7,
                    label=f"n={n} threshold = {threshold:.3f}")
plt.xlabel("Ratio (M/N)")
plt.ylabel("P(SAT)")
plt.ylim(0, 1)
plt.title("G1: Phase transition - probability of satisfiability per n\n"
          "Shows the probability that a formula is SAT. The crossing with 0.5 is the critical threshold.")
plt.legend()

# ===================================================================
# G2: Computational cost (difficulty) curve
# ===================================================================
plt.figure()
for idx, n in enumerate(n_values):
    st = style_for(idx)
    n_df = df[df["n"] == n]
    decided = n_df[n_df["result"] != "TO"]
    med = decided.groupby("ratio")["time"].median()
    med = med.sort_index()
    peak_ratio = med.idxmax()
    threshold = interpolate_threshold(decided.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index())
    print(f"Difficulty peak (max median) for n={n}: ratio = {peak_ratio}, time = {med.max()}")
    plt.plot(med.index, med.values, marker=st["marker"], linestyle=st["linestyle"],
             color=st["color"], label=f"Median time n={n}")
    if threshold is not None:
        plt.axvline(threshold, color=st["color"], linestyle=":", linewidth=1, alpha=0.7,
                    label=f"n={n} threshold = {threshold:.3f}")
plt.xlabel("Ratio (M/N)")
plt.ylabel("Median execution time (s)")
plt.title("G2: Computational cost (difficulty) per n\n"
          "Easy-hard-easy bell-shaped curve. The peak should coincide with the critical threshold of G1.")
plt.legend()

# ===================================================================
# G3: Fraction of timeouts per ratio
# ===================================================================
plt.figure()
for idx, n in enumerate(n_values):
    st = style_for(idx)
    n_df = df[df["n"] == n]
    to_frac = n_df.groupby("ratio")["result"].apply(lambda r: (r == "TO").mean())
    to_frac = to_frac.sort_index()
    to_peak = to_frac.idxmax()
    threshold = interpolate_threshold(n_df[n_df["result"] != "TO"].groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index())
    print(f"Timeout peak for n={n}: ratio = {to_peak}, frac = {to_frac.max()}")
    plt.plot(to_frac.index, to_frac.values, marker=st["marker"], linestyle=st["linestyle"],
             color=st["color"], label=f"Fraction TO n={n}")
    if threshold is not None:
        plt.axvline(threshold, color=st["color"], linestyle=":", linewidth=1, alpha=0.7,
                    label=f"n={n} threshold = {threshold:.3f}")
plt.xlabel("Ratio (M/N)")
plt.ylabel("Fraction of timeouts")
plt.ylim(0, 1)
plt.title("G3: Fraction of timeouts per ratio and n\n"
          "Timeouts are the genuinely hard formulas. The peak should coincide with the threshold.")
plt.legend()

# ===================================================================
# G4: Scatter time vs ratio, color per n, marker per result
# ===================================================================
result_markers = {"SAT": "o", "UNSAT": "x", "TO": "^"}

plt.figure()
for idx, n in enumerate(n_values):
    st = style_for(idx)
    n_df = df[df["n"] == n]
    for res, mk in result_markers.items():
        sub = n_df[n_df["result"] == res]
        if not sub.empty:
            plt.scatter(sub["ratio"], sub["time"], c=st["color"], marker=mk,
                        s=12, alpha=0.5, label=f"{res} (n={n})")
plt.xlabel("Ratio (M/N)")
plt.ylabel("Execution time (s)")
plt.yscale("log")
plt.title("G4: Time vs ratio by n and result\n"
          "Scatter plot: color distinguishes n, marker distinguishes result (SAT=o, UNSAT=x, TO=^).")
plt.legend()

# ===================================================================
# G5: Heatmap ratio x pd (Probabilidad de Diamante), one subplot per n
# ===================================================================
if "pd" in df.columns:
    if len(sorted(df["pd"].unique())) < 2 or df["ratio"].nunique() < 2:
        print("Warning: G5 (heatmap) skipped: a heatmap needs at least 2 distinct pd values "
              "and 2 distinct ratios to be drawn.")
    else:
        pivots = []
        for n in n_values:
            n_df = df[df["n"] == n]
            decided = n_df[n_df["result"] != "TO"]
            pivots.append(decided.pivot_table(index="ratio", columns="pd", values="time", aggfunc="median"))
        valid = [pv.values for pv in pivots if pv.size]
        vmin = min(v[~np.isnan(v)].min() for v in valid) if valid else 0
        vmax = max(v[~np.isnan(v)].max() for v in valid) if valid else 1

        ncols = len(n_values)
        fig, axes = plt.subplots(1, ncols, squeeze=False)
        axes = axes[0]
        im = None
        for idx, n in enumerate(n_values):
            ax = axes[idx]
            pivot = pivots[idx]
            if pivot.empty:
                ax.set_title(f"n={n} (no data)")
                continue
            n_df = df[df["n"] == n]
            frac = n_df[n_df["result"] != "TO"].groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index()
            threshold = interpolate_threshold(frac)
            im = ax.imshow(pivot.values, aspect="auto", origin="lower",
                           extent=[pivot.columns.min(), pivot.columns.max(),
                                   pivot.index.min(), pivot.index.max()],
                           cmap="viridis", vmin=vmin, vmax=vmax)
            if threshold is not None:
                ax.axhline(threshold, color="red", linestyle="--", linewidth=1,
                           label=f"n={n} threshold = {threshold:.3f}")
            ax.set_title(f"n={n}")
            ax.set_xlabel("pd (Probabilidad de Diamante)")
            ax.set_ylabel("Ratio (M/N)")
            ax.legend()
        if im is not None:
            fig.colorbar(im, ax=axes, label="Median time (s)")
        fig.suptitle("G5: Heatmap ratio x pd - median time per n\n"
                     "Shows how difficulty changes with the diamond proportion pd. The red line is the critical threshold.")
# ===================================================================
# G6: Grouped boxplot of times per ratio and n
# ===================================================================
ordered_ratios = sorted(df["ratio"].unique())
k = len(n_values)
group_width = k + 1
box_positions = []
box_data = []
box_colors = []
thresholds = {}
for n in n_values:
    frac = df[df["n"] == n][df[df["n"] == n]["result"] != "TO"].groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index()
    thresholds[n] = interpolate_threshold(frac)
for i, r in enumerate(ordered_ratios):
    base = i * group_width
    for j, n in enumerate(n_values):
        data = df[(df["ratio"] == r) & (df["n"] == n)]["time"].to_numpy()
        if len(data) == 0:
            continue
        st = style_for(j)
        box_positions.append(base + j + 1)
        box_data.append(data)
        box_colors.append(st["color"])

plt.figure()
bp = plt.boxplot(box_data, positions=box_positions, tick_labels=[""] * len(box_positions), patch_artist=True)
for patch, c in zip(bp["boxes"], box_colors):
    patch.set_facecolor(c)
for j, n in enumerate(n_values):
    threshold = thresholds.get(n)
    if threshold is None:
        continue
    nearest = min(ordered_ratios, key=lambda r: abs(r - threshold))
    i = ordered_ratios.index(nearest)
    pos = i * group_width + j + 1
    plt.axvline(pos, color=style_for(j)["color"], linestyle="--", linewidth=1, alpha=0.7,
                label=f"n={n} threshold = {threshold:.3f}")
group_centers = [i * group_width + (group_width + 1) / 2 for i in range(len(ordered_ratios))]
plt.xticks(group_centers, [str(r) for r in ordered_ratios], rotation=45)
plt.xlabel("Ratio (M/N)")
plt.ylabel("Execution time (s)")
plt.yscale("log")
plt.title("G6: Distribution of times per ratio and n\n"
          "Full boxplot: median, quartiles and outliers. Reveals isolated hard instances.")
plt.legend()

# ===================================================================
# G7: Normalized difficulty curve (median time per size unit)
# ===================================================================
if "time_per_size" in df.columns:
    plt.figure()
    for idx, n in enumerate(n_values):
        st = style_for(idx)
        n_df = df[df["n"] == n]
        decided = n_df[n_df["result"] != "TO"]
        med = decided.groupby("ratio")["time_per_size"].median()
        med = med.sort_index()
        peak_ratio = med.idxmax()
        threshold = interpolate_threshold(decided.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index())
        print(f"Normalized difficulty peak (max median time/size) for n={n}: ratio = {peak_ratio}, time/size = {med.max()}")
        plt.plot(med.index, med.values, marker=st["marker"], linestyle=st["linestyle"],
                 color=st["color"], label=f"Median time/size n={n}")
        if threshold is not None:
            plt.axvline(threshold, color=st["color"], linestyle=":", linewidth=1, alpha=0.7,
                        label=f"n={n} threshold = {threshold:.3f}")
    plt.xlabel("Ratio (M/N)")
    plt.ylabel("Median time/size (s/char)")
    plt.title("G7: Normalized computational cost per n\n"
              "Median time divided by formula length. Removes the effect of longer formulas, "
              "revealing the difficulty due to structural complexity only.")
    plt.legend()

# ===================================================================
# G8: Evolución Estructural (Cajas y Diamantes vs. Ratio M/N)
# ===================================================================
if "boxes" in df.columns and "diamonds" in df.columns:
    plt.figure()
    for idx, n in enumerate(n_values):
        st = style_for(idx)
        n_df = df[df["n"] == n]
        decided = n_df[n_df["result"] != "TO"]
        
        # Promedio de cajas y diamantes por ratio
        med_boxes = decided.groupby("ratio")["boxes"].median().sort_index()
        med_diamonds = decided.groupby("ratio")["diamonds"].median().sort_index()

        plt.plot(med_boxes.index, med_boxes.values, marker=st["marker"], linestyle="-",
                 color=st["color"], label=f"Cajas (A) n={n}")
        plt.plot(med_diamonds.index, med_diamonds.values, marker="x", linestyle=":",
                 color=st["color"], alpha=0.7, label=f"Diamantes (E) n={n}")

    plt.xlabel("Ratio (M/N)")
    plt.ylabel("Cantidad Mediana de Operadores")
    plt.title("G8: Crecimiento de Cajas (A) vs Diamantes (E)\n"
              "Muestra la saturación de mundos (E) y el crecimiento lineal de restricciones (A).")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

# ===================================================================
# G9: Tiempo vs Relación Modal (Cajas / Diamantes)
# ===================================================================
if "modal_ratio" in df.columns:
    plt.figure()
    for idx, n in enumerate(n_values):
        st = style_for(idx)
        n_df = df[df["n"] == n]
        decided = n_df[n_df["result"] != "TO"]
        
        # Agrupamos por ratio de variables para suavizar la dispersión
        grouped = decided.groupby("ratio").agg({"modal_ratio": "median", "time": "median"}).sort_values("modal_ratio")
        
        plt.plot(grouped["modal_ratio"], grouped["time"], marker=st["marker"], linestyle=st["linestyle"],
                 color=st["color"], label=f"n={n}")

    plt.xlabel("Modal Ratio (Total Cajas / Total Diamantes)")
    plt.ylabel("Execution time (s)")
    plt.yscale("log")
    plt.title("G9: Dificultad basada en la dominancia de Cajas\n"
              "Muestra cómo el tiempo explota cuando hay una proporción específica de restricciones por mundo.")
    plt.legend()
    

# ===================================================================
# G10: Impacto de la Proporción Modal en la Dificultad (PD vs Tiempo)
# ===================================================================
if "pd" in df.columns:
    plt.figure()
    
    # Elegimos el 'n' más grande que tengas para ver el efecto con mayor claridad
    n_target = max(n_values)
    n_df = df[df["n"] == n_target]
    decided = n_df[n_df["result"] != "TO"]
    
    # Detectamos qué probabilidades de diamantes (pd) corriste
    pd_values_present = sorted(decided["pd"].unique())
    
    for idx, pd_val in enumerate(pd_values_present):
        st = style_for(idx)
        sub_df = decided[decided["pd"] == pd_val]
        
        # Calculamos la mediana de tiempo para cada ratio
        med = sub_df.groupby("ratio")["time"].median().sort_index()
        
        # Etiqueta clara para el profesor
        if pd_val < 0.5:
            lbl = f"Muchas Cajas (pd={pd_val})"
        elif pd_val > 0.5:
            lbl = f"Muchos Diamantes (pd={pd_val})"
        else:
            lbl = f"Balanceado (pd={pd_val})"
            
        plt.plot(med.index, med.values, marker=st["marker"], linestyle=st["linestyle"],
                 color=st["color"], label=lbl)

    plt.xlabel("Ratio (M/N)")
    plt.ylabel("Execution time (s)")
    plt.yscale("log")
    plt.title(f"G10: Impacto de Cajas vs Diamantes en la Dificultad (n={n_target})\n"
              "Muestra cómo el exceso de Cajas o Diamantes altera la campana de transición de fase.")
    plt.legend()
    plt.tight_layout()

# ===================================================================
# G11: Worlds vs Time (log-log scatter + median per n + power-law fit)
# ===================================================================
g8_df = df[df["result"] != "TO"].copy()
g8_df["n"] = pd.to_numeric(g8_df["n"], errors="coerce")
g8_df["time"] = pd.to_numeric(g8_df["time"], errors="coerce")
g8_df["worlds"] = pd.to_numeric(g8_df["worlds"], errors="coerce")
g8_df = g8_df.dropna(subset=["n", "time", "worlds"])
g8_df = g8_df[g8_df["time"] > 0]

if g8_df.empty:
    print("Warning: G8 skipped: no rows with valid 'worlds' and 'time'.")
else:
    plt.figure()
    ns = sorted(g8_df["n"].unique())
    n_to_color = {n: COLORS[idx % len(COLORS)] for idx, n in enumerate(ns)}

    # Log-log scatter, points colored by n (distinct categorical colors)
    plt.scatter(g8_df["worlds"], g8_df["time"], c=g8_df["n"].map(n_to_color),
                s=10, alpha=0.55)

    # Median time per worlds-quantile bucket, one curve per n
    for idx, n in enumerate(ns):
        ndf = g8_df[g8_df["n"] == n]
        bdf = ndf.assign(wbucket=pd.qcut(ndf["worlds"], q=8, duplicates="drop"))
        med = bdf.groupby("wbucket", observed=True)["time"].median()
        mids = [i.mid for i in med.index]
        plt.plot(mids, med.values,
                 color=n_to_color[n], linestyle=LINESTYLES[idx % len(LINESTYLES)],
                 marker=MARKERS[idx % len(MARKERS)], label=f"median n={n}")

    # Power-law fit: log(time) = alpha*log(worlds) + c
    X = np.log(g8_df["worlds"].to_numpy())
    Y = np.log(g8_df["time"].to_numpy())
    alpha, c = np.polyfit(X, Y, 1)
    pred = alpha * X + c
    ss_res = float(((Y - pred) ** 2).sum())
    ss_tot = float(((Y - Y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot
    print(f"G8 power-law fit: time = C * worlds^alpha, alpha = {alpha:.3f}, "
          f"C = {np.exp(c):.3e}, R^2 = {r2:.3f}")

    plt.xlabel("Worlds")
    plt.ylabel("Execution time (s)")
    plt.xscale("log")
    plt.yscale("log")
    plt.title("G8: Worlds vs Time (log-log)\n"
              "Points colored by n. Lines: median time per worlds bucket per n. "
              "Slope of the fit = scaling exponent alpha.")
    plt.legend()

# ===================================================================
# G12: La Campana de Dificultad separada por Rangos de Mundos (Buckets)
# ===================================================================
if "worlds" in df.columns:
    plt.figure()
    
    # Tomamos solo el 'n' más grande para que el gráfico sea claro
    n_target = max(n_values)
    n_df = df[df["n"] == n_target]
    
    # Usamos .copy() para evitar warnings de Pandas al crear nuevas columnas
    decided = n_df[n_df["result"] != "TO"].copy() 
    
    # 1. Definimos los "Buckets" (Rangos) de mundos. 
    # Ajusta estos números si generaste fórmulas mucho más grandes.
    bins = [0, 50, 150, 350, 600, 1000, float('inf')]
    labels = ["<50", "50-150", "150-350", "350-600", "600-1000", ">1000"]
    
    # Asignamos cada fórmula a su rango correspondiente
    decided["w_bucket"] = pd.cut(decided["worlds"], bins=bins, labels=labels)
    
    # 2. Filtramos solo los rangos que realmente tienen datos en tus CSVs
    active_buckets = decided["w_bucket"].dropna().unique()
    active_buckets = sorted(active_buckets, key=lambda x: labels.index(x))
    
    for idx, bucket in enumerate(active_buckets):
        st = style_for(idx)
        # Filtramos las fórmulas de este bucket específico
        sub_df = decided[decided["w_bucket"] == bucket]
        
        if sub_df.empty: 
            continue
            
        # 3. Calculamos la mediana agrupando TODAS las fórmulas del bucket por Ratio
        med = sub_df.groupby("ratio")["time"].median().sort_index()
        
        # Solo graficamos si hay suficientes puntos para hacer una línea decente
        if len(med) > 2:
            plt.plot(med.index, med.values, marker=st["marker"], linestyle=st["linestyle"],
                     color=st["color"], label=f"Mundos: {bucket}")

    plt.xlabel("Ratio (M/N)")
    plt.ylabel("Tiempo de Ejecución Mediano (s)")
    plt.yscale("log")
    plt.title(f"G12: Transición de Fase por Rangos de Mundos (N={n_target})\n"
              "Agrupando fórmulas en buckets para suavizar la curva de dificultad.")
    plt.legend()
    plt.tight_layout()
else:
    print("Warning: G12 skipped. No se encontró la columna 'worlds'.")
    
    
    
# ===================================================================
# G1_DESGLOSADO: Transición de Fase P(SAT) y Thresholds separados
# por 'n' Y por la variable secundaria (Mundos o pd)
# ===================================================================

# 1. Filtramos instancias no resueltas (TO)
df_clean = df[df["result"] != "TO"].copy()

# 2. SELECCIÓN DE VARIABLE SECUNDARIA A AISLAR:
# Descomenta la opción que quieras analizar:

# OPCIÓN A: Agrupar por Rangos de Mundos (Buckets)
if "worlds" in df_clean.columns:
    bins = [0, 50, 150, 350, 600, 1000, float('inf')]
    labels = ["<50", "50-150", "150-350", "350-600", "600-1000", ">1000"]
    df_clean["var_sec"] = pd.cut(df_clean["worlds"], bins=bins, labels=labels)
    nombre_var = "Mundos"
# OPCIÓN B: Agrupar por parámetro pd (Proporción Cajas/Diamantes)
elif "pd" in df_clean.columns:
    df_clean["var_sec"] = df_clean["pd"]
    nombre_var = "pd"
else:
    df_clean["var_sec"] = "Grupo Único"
    nombre_var = "Grupo"

# 3. Creación del gráfico con un subplot por cada 'n'
ncols = len(n_values)
fig, axes = plt.subplots(1, ncols, figsize=(7 * ncols, 5), squeeze=False)
axes = axes[0]

print("\n=== THRESHOLDS CRÍTICOS INTERPOLADOS P(SAT) = 0.5 ===")

for idx_n, n in enumerate(n_values):
    ax = axes[idx_n]
    n_df = df_clean[df_clean["n"] == n]
    
    # Línea horizontal de referencia P(SAT) = 0.5
    ax.axhline(0.5, color="black", linestyle="--", linewidth=1, alpha=0.7, label="P(SAT) = 0.5")
    
    # Obtenemos los subgrupos presentes en este 'n'
    sec_values = [v for v in n_df["var_sec"].dropna().unique()]
    sec_values = sorted(sec_values, key=lambda x: str(x))
    
    for idx_sec, sec_val in enumerate(sec_values):
        sub_df = n_df[n_df["var_sec"] == sec_val]
        
        # P(SAT) individualizado por Ratio
        frac = sub_df.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index()
        
        if len(frac) < 2:
            continue
            
        # Interpolación matemática del threshold para este subgrupo exacto
        threshold = interpolate_threshold(frac)
        st = style_for(idx_sec)
        
        lbl_curva = f"{nombre_var}: {sec_val}"
        ax.plot(frac.index, frac.values, marker=st["marker"], linestyle=st["linestyle"],
                color=st["color"], label=lbl_curva)
        
        # Dibuja la línea vertical del threshold individualizado
        if threshold is not None:
            print(f"n={n} | {nombre_var}={sec_val} -> Threshold en Ratio = {threshold:.3f}")
            ax.axvline(threshold, color=st["color"], linestyle=":", linewidth=1.5, alpha=0.85,
                       label=f"Thresh ({sec_val}) = {threshold:.2f}")

    ax.set_xlabel("Ratio (M/N)")
    ax.set_ylabel("P(SAT)")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title(f"Transición de Fase para n = {n}")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(fontsize="small", loc="best")

fig.suptitle(f"Transición de Fase P(SAT) y Thresholds Desglosados por n y {nombre_var}\n"
             f"(Las líneas punteadas verticales representan el threshold individual P(SAT)=0.5)",
             fontsize=12)
plt.tight_layout()

# ===================================================================
# G13: Campana de Dificultad (Mundos fijos 350-600) separada por CAJAS
# ===================================================================
if "worlds" in df.columns and "boxes" in df.columns:
    plt.figure()
    
    # Tomamos el 'n' más grande para mayor claridad en los tiempos
    n_target = max(n_values)
    
    # 1. FILTRO MAESTRO: Solo 'n' máximo, sin Timeouts, y MUNDOS entre 350 y 600
    df_g13 = df[(df["n"] == n_target) & 
                (df["result"] != "TO") & 
                (df["worlds"] >= 350) & 
                (df["worlds"] <= 600)].copy()
    
    if df_g13.empty:
        print(f"Warning: No hay datos suficientes para n={n_target} con mundos entre 350 y 600.")
    else:
        # 2. Definimos los "Buckets" (Rangos) para las CAJAS (A)
        # NOTA: Puedes ajustar estos límites numéricos si tus cajas reales 
        # son mucho mayores o menores en los CSVs.
        bins_boxes = [0, 100, 300, 600, 1000, float('inf')]
        labels_boxes = ["<100", "100-300", "300-600", "600-1000", ">1000"]
        
        # Asignamos cada fórmula a su rango de cajas correspondiente
        df_g13["box_bucket"] = pd.cut(df_g13["boxes"], bins=bins_boxes, labels=labels_boxes)
        
        # Obtenemos solo los buckets que realmente tengan fórmulas adentro
        active_box_buckets = df_g13["box_bucket"].dropna().unique()
        active_box_buckets = sorted(active_box_buckets, key=lambda x: labels_boxes.index(x))
        
        for idx, bucket in enumerate(active_box_buckets):
            st = style_for(idx)
            
            # Filtramos las fórmulas que caen en este rango de cajas
            sub_df = df_g13[df_g13["box_bucket"] == bucket]
            
            if sub_df.empty: 
                continue
                
            # Calculamos la mediana de tiempo agrupando por Ratio
            med = sub_df.groupby("ratio")["time"].median().sort_index()
            
            # Graficamos solo si hay al menos 3 puntos para formar una curva
            if len(med) > 2:
                plt.plot(med.index, med.values, marker=st["marker"], linestyle=st["linestyle"],
                         color=st["color"], label=f"Cajas (A): {bucket}")

        plt.xlabel("Ratio (M/N)")
        plt.ylabel("Tiempo de Ejecución Mediano (s)")
        plt.yscale("log")
        plt.title(f"G13: Impacto de Cajas con Mundos constantes (350-600) (n={n_target})\n"
                  "Demuestra si asfixiar un universo de tamaño fijo facilita el problema.")
        plt.legend()
        plt.tight_layout()
        plt.show()
else:
    print("Warning: G13 skipped. Faltan las columnas 'worlds' o 'boxes' en tu CSV.")

# ===================================================================
# G14: Gráfico 3D (Ratio vs Relación Modal vs Tiempo)
# ===================================================================
if "modal_ratio" in df.columns:
    # Importamos explicitamente la proyección 3D (necesario en algunas versiones de matplotlib)
    from mpl_toolkits.mplot3d import Axes3D 
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # 1. Filtramos: quitamos Timeouts y tomamos el 'n' más grande para ver el pico claro
    n_target = max(n_values)
    df_3d = df[(df["n"] == n_target) & (df["result"] != "TO")].copy()
    
    # 2. Extraemos las coordenadas
    x = df_3d["ratio"]
    y = df_3d["modal_ratio"]
    z = df_3d["time"]
    
    # 3. Dibujamos el Scatter 3D. 
    # Usamos 'c=z' para que el color represente el tiempo (azul = rápido, rojo = lento)
    sc = ax.scatter(x, y, z, c=z, cmap='coolwarm', marker='o', s=30, alpha=0.8, edgecolors='k', linewidth=0.2)
    
    # 4. Etiquetas y diseño
    ax.set_xlabel('Ratio (M/N)')
    ax.set_ylabel('Modal Ratio (Cajas / Diamantes)')
    ax.set_zlabel('Tiempo de Ejecución (s)')
    
    ax.set_title(f"G14: La Montaña de Dificultad S5 (n={n_target})\n"
                 "Interacción entre Densidad Proposicional y Asimetría Modal")
    
    # Barra de color de referencia
    cbar = fig.colorbar(sc, ax=ax, shrink=0.5, aspect=10, pad=0.1)
    cbar.set_label('Tiempo de Ejecución (s)')
    
    # Ajustamos el ángulo de visión inicial (Elevación, Azimut)
    ax.view_init(elev=30, azim=135)
    
    plt.tight_layout()
    plt.show()
else:
    print("Warning: G14 skipped. No se encontró la columna 'modal_ratio'.")
    
# ===================================================================
# G15_Lineas: Gráfico 3D (Ratio vs Relación Diamantes/Cajas vs Tiempo)
# ===================================================================
if "diamonds" in df.columns and "boxes" in df.columns:
    # Importamos explicitamente la proyección 3D
    from mpl_toolkits.mplot3d import Axes3D 
    import numpy as np
    import matplotlib.cm as cm
    
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # 1. Filtramos: quitamos Timeouts y tomamos el 'n' más grande
    n_target = max(n_values)
    df_3d = df[(df["n"] == n_target) & (df["result"] != "TO")].copy()
    
    # Calculamos Diamantes / Cajas
    df_3d["diam_box_ratio"] = df_3d["diamonds"] / df_3d["boxes"].replace(0, np.nan)
    df_3d = df_3d.dropna(subset=["diam_box_ratio", "time", "ratio"])
    
    # 2. Agrupamos por la relación modal.
    # Redondeamos a 1 decimal para juntar las fórmulas que corresponden al mismo 
    # salto de tu generador (0.5, 1.0, 1.5, etc.)
    df_3d["y_group"] = df_3d["diam_box_ratio"].round(1)
    
    y_unique = sorted(df_3d["y_group"].unique())
    max_time_global = df_3d["time"].max()
    
    # Usamos un mapa de colores (azul a rojo)
    # Usamos un mapa de colores (azul a rojo)
    cmap = plt.get_cmap('coolwarm')
    
    # 3. Dibujamos una LÍNEA por cada nivel de asimetría modal
    for y_val in y_unique:
        sub_df = df_3d[df_3d["y_group"] == y_val]
        
        # Obtenemos la curva de dificultad para este valor específico de Diam/Cajas
        grouped = sub_df.groupby("ratio")["time"].median().sort_index()
        
        # Solo dibujamos si hay al menos 2 puntos para trazar una línea
        if len(grouped) > 1:
            xs = grouped.index.to_numpy()
            zs = grouped.values
            ys = np.full_like(xs, y_val)
            
            # Calculamos el color de la línea basado en qué tan alto llega su pico de dificultad
            # Las líneas que lleguen más alto serán más rojas; las planas, azules.
            color_val = cmap(zs.max() / max_time_global)
            
            # Dibujamos la línea 3D gruesa
            ax.plot(xs, ys, zs, color=color_val, linewidth=3, alpha=0.8, zorder=3)
            
            # Agregamos los puntos sobre la línea para marcar exactamente qué ratios probaste
            ax.scatter(xs, ys, zs, color=color_val, s=25, edgecolors='white', linewidth=0.5, zorder=4)

    # 4. Etiquetas y diseño
    ax.set_xlabel('Ratio (M/N)', labelpad=10)
    ax.set_ylabel('Dominancia Modal (Diamantes / Cajas)', labelpad=10)
    ax.set_zlabel('Tiempo de Ejecución Mediano (s)', labelpad=10)
    
    ax.set_title(f"G15: La Montaña de Dificultad S5 (n={n_target})\n"
                 "Curvas de transición de fase separadas por relación Diamantes/Cajas")
    
    # Ajustamos el ángulo de visión para ver bien las crestas de la montaña
    ax.view_init(elev=25, azim=135)
    
    plt.tight_layout()
else:
    print("Warning: G15 skipped. Faltan las columnas 'diamonds' o 'boxes' en el CSV.")
# ===================================================================
# ANÁLISIS ESTADÍSTICO: ¿Dónde está exactamente la mayor dificultad?
# ===================================================================
print("\n" + "="*50)
print("=== ANÁLISIS DE LA ZONA DE MAYOR DIFICULTAD ===")
print("="*50)

# Filtramos los Timeouts para que no distorsionen las medianas 
# (o puedes incluirlos si quieres saber la estructura de los TO)
df_analisis = df[df["result"] != "TO"].copy()

# Asegurarnos de que las columnas sean numéricas
for col in ["ratio", "time", "boxes", "diamonds"]:
    if col in df_analisis.columns:
        df_analisis[col] = pd.to_numeric(df_analisis[col], errors='coerce')

for n in sorted(df_analisis["n"].unique()):
    n_df = df_analisis[df_analisis["n"] == n]
    if n_df.empty: continue
    
    print(f"\n--- Resultados para n = {n} ---")
    
    # MÉTODO 1: El Pico de la Campana (Dificultad Mediana)
    if "boxes" in n_df.columns and "diamonds" in n_df.columns:
        # Agrupamos por ratio y sacamos los promedios/medianas
        grouped = n_df.groupby("ratio").agg(
            median_time=("time", "median"),
            avg_boxes=("boxes", "mean"),
            avg_diamonds=("diamonds", "mean")
        ).reset_index()
        
        # Encontramos la fila con el tiempo mediano más alto
        peak = grouped.loc[grouped["median_time"].idxmax()]
        
        print("1. PICO ESTRUCTURAL (El centro de la campana):")
        print(f"   - Ratio Crítico: {peak['ratio']:.2f}")
        print(f"   - Tiempo Mediano: {peak['median_time']:.4f} s")
        print(f"   - Promedio de Cajas (A): {peak['avg_boxes']:.1f}")
        print(f"   - Promedio de Diamantes (E): {peak['avg_diamonds']:.1f}")

    # MÉTODO 2: Las Instancias más difíciles (Top 5% de fórmulas)
    top_percent = 0.1
    k_top = max(1, int(len(n_df) * top_percent))
    top_formulas = n_df.nlargest(k_top, "time")
    
    print(f"\n2. TOP {int(top_percent*100)}% FÓRMULAS MÁS LENTAS (Las 'asesinas' de Z3):")
    print(f"   - Ratio Promedio: {top_formulas['ratio'].mean():.2f} (Min: {top_formulas['ratio'].min()}, Max: {top_formulas['ratio'].max()})")
    print(f"   - Tiempo Promedio: {top_formulas['time'].mean():.4f} s")
    
    if "boxes" in top_formulas.columns and "diamonds" in top_formulas.columns:
        print(f"   - Cajas Promedio: {top_formulas['boxes'].mean():.1f}")
        print(f"   - Diamantes Promedio: {top_formulas['diamonds'].mean():.1f}")
        
    # Extra: Proporción modal de las más difíciles
    if "modal_ratio" in top_formulas.columns:
         print(f"   - Relación Modal Promedio (Cajas/Diamantes): {top_formulas['modal_ratio'].mean():.2f}")
         
print("\n" + "="*50)

plt.show()
