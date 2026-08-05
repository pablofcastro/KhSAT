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

# ---- Decided formulas (exclude timeouts) for P(SAT) and median time ----
decided = df[df["result"] != "TO"]

# ===================================================================
# G1: Phase transition curve (probability of satisfiability)
# ===================================================================
frac = decided.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean())
frac = frac.sort_index()

# Linear interpolation of the exact crossing of P(SAT) = 0.5
threshold = None
xs = frac.index.to_numpy()
ys = frac.values
for i in range(len(xs) - 1):
    if ys[i] >= 0.5 > ys[i + 1]:
        t = (0.5 - ys[i]) / (ys[i + 1] - ys[i])
        threshold = xs[i] + t * (xs[i + 1] - xs[i])
        break
print(f"Interpolated critical threshold (P(SAT)=0.5): ratio = {threshold}")

plt.figure()
plt.plot(xs, ys, marker="o", linestyle="-", color="green", label="P(SAT)")
plt.axhline(0.5, color="red", linestyle="--", linewidth=1, label="P(SAT) = 0.5")
if threshold is not None:
    plt.axvline(threshold, color="red", linestyle=":", linewidth=1, alpha=0.7,
                label=f"Critical threshold = {threshold:.3f}")
plt.xlabel("Ratio (M/N)")
plt.ylabel("P(SAT)")
plt.ylim(0, 1)
plt.title("G1: Phase transition - probability of satisfiability\n"
          "Shows the probability that a formula is SAT. The crossing with 0.5 is the critical threshold.")
plt.legend()

# ===================================================================
# G2: Computational cost (difficulty) curve
# ===================================================================
med = decided.groupby("ratio")["time"].median()
med = med.sort_index()
peak_ratio = med.idxmax()

plt.figure()
plt.plot(med.index, med.values, marker="o", linestyle="-", color="blue", label="Median time")
if threshold is not None:
    plt.axvline(threshold, color="red", linestyle="--", linewidth=1, alpha=0.7,
                label=f"Critical threshold = {threshold:.3f}")
plt.xlabel("Ratio (M/N)")
plt.ylabel("Median execution time (s)")
plt.title("G2: Computational cost (difficulty)\n"
          "Easy-hard-easy bell-shaped curve. The peak should coincide with the critical threshold of G1.")
plt.legend()
print(f"Difficulty peak (max median): ratio = {peak_ratio}, time = {med.max()}")

# ===================================================================
# G3: Fraction of timeouts per ratio
# ===================================================================
to_frac = df.groupby("ratio")["result"].apply(lambda r: (r == "TO").mean())
to_frac = to_frac.sort_index()
to_peak = to_frac.idxmax()

plt.figure()
plt.plot(to_frac.index, to_frac.values, marker="o", linestyle="-", color="black", label="Fraction TO")
if threshold is not None:
    plt.axvline(threshold, color="red", linestyle="--", linewidth=1, alpha=0.7,
                label=f"Critical threshold = {threshold:.3f}")
plt.xlabel("Ratio (M/N)")
plt.ylabel("Fraction of timeouts")
plt.ylim(0, 1)
plt.title("G3: Fraction of timeouts per ratio\n"
          "Timeouts are the genuinely hard formulas. The peak should coincide with the threshold.")
plt.legend()
print(f"Timeout peak: ratio = {to_peak}, frac = {to_frac.max()}")

# ===================================================================
# G4: Scatter time vs ratio colored by result
# ===================================================================
colors = {"SAT": "green", "UNSAT": "red", "TO": "black"}

plt.figure()
for res, c in colors.items():
    sub = df[df["result"] == res]
    if not sub.empty:
        plt.scatter(sub["ratio"], sub["time"], c=c, s=12, alpha=0.5, label=res)
if threshold is not None:
    plt.axvline(threshold, color="red", linestyle="--", linewidth=1, alpha=0.7,
                label=f"Critical threshold = {threshold:.3f}")
plt.xlabel("Ratio (M/N)")
plt.ylabel("Execution time (s)")
plt.yscale("log")
plt.title("G4: Time vs ratio by result\n"
          "Scatter plot: SAT (green), UNSAT (red), TO (black). TOs concentrate near the threshold.")
plt.legend()

# ===================================================================
# G5: Heatmap ratio x p (diamond degree)
# ===================================================================
if "p" in df.columns:
    pivot = df.pivot_table(index="ratio", columns="p", values="time", aggfunc="median")
    plt.figure()
    im = plt.imshow(pivot.values, aspect="auto", origin="lower",
                    extent=[pivot.columns.min(), pivot.columns.max(),
                            pivot.index.min(), pivot.index.max()],
                    cmap="viridis")
    if threshold is not None:
        plt.axhline(threshold, color="red", linestyle="--", linewidth=1,
                    label=f"Critical threshold = {threshold:.3f}")
    plt.colorbar(im, label="Median time (s)")
    plt.xlabel("p (diamond degree)")
    plt.ylabel("Ratio (M/N)")
    plt.title("G5: Heatmap ratio x p - median time\n"
              "Shows how difficulty changes with the diamond degree p. The red line is the critical threshold.")
    plt.legend()

# ===================================================================
# G6: Boxplot of times per ratio
# ===================================================================
ordered_ratios = sorted(df["ratio"].unique())
plt.figure()
bp = plt.boxplot([df[df["ratio"] == r]["time"].to_numpy() for r in ordered_ratios],
                 tick_labels=[str(r) for r in ordered_ratios])
if threshold is not None:
    plt.axvline(ordered_ratios.index(min(ordered_ratios, key=lambda r: abs(r - threshold))) + 1,
                color="red", linestyle="--", linewidth=1, alpha=0.7,
                label=f"Critical threshold = {threshold:.3f}")
plt.xlabel("Ratio (M/N)")
plt.ylabel("Execution time (s)")
plt.yscale("log")
plt.xticks(rotation=45)
plt.title("G6: Distribution of times per ratio\n"
          "Full boxplot: median, quartiles and outliers. Reveals isolated hard instances.")
plt.legend()

plt.show()
