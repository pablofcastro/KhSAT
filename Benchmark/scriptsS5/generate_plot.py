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
# G5: Heatmap ratio x p (diamond degree), one subplot per n
# ===================================================================
if "p" in df.columns:
    if len(sorted(df["p"].unique())) < 2 or df["ratio"].nunique() < 2:
        print("Warning: G5 (heatmap) skipped: a heatmap needs at least 2 distinct p values "
              "and 2 distinct ratios to be drawn.")
    else:
        pivots = []
        for n in n_values:
            n_df = df[df["n"] == n]
            decided = n_df[n_df["result"] != "TO"]
            pivots.append(decided.pivot_table(index="ratio", columns="p", values="time", aggfunc="median"))
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
            ax.set_xlabel("p (diamond degree)")
            ax.set_ylabel("Ratio (M/N)")
            ax.legend()
        if im is not None:
            fig.colorbar(im, ax=axes, label="Median time (s)")
        fig.suptitle("G5: Heatmap ratio x p - median time per n\n"
                     "Shows how difficulty changes with the diamond degree p. The red line is the critical threshold.")

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
# G8: Worlds vs Time (log-log scatter + median per n + power-law fit)
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

plt.show()
