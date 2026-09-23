import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
import glob
import argparse

# ===================================================================
# 0. CONFIGURATION
# ===================================================================


def load_data(include_other=False):
    file_list = glob.glob("output-batch*.csv")
    if include_other and os.path.exists("other_batchs"):
        file_list.extend(glob.glob(os.path.join("other_batchs", "*.csv")))

    dfs = []
    for file in file_list:
        try:
            df_temp = pd.read_csv(file)
            if not df_temp.empty:
                dfs.append(df_temp)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            pass

    if not dfs:
        return None

    return pd.concat(dfs, ignore_index=True)


def clean_data(df):
    df = df.copy()
    df["result"] = df["result"].astype(str).str.replace(".", "", regex=False)

    numeric_cols = [
        "n",
        "m",
        "ratio",
        "modal_ratio",
        "z3_time",
        "translation_time",
        "time",
        "total_time",
        "worlds",
        "diamonds",
        "boxes",
        "size",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["n", "z3_time", "translation_time", "time"])
    df["n"] = df["n"].astype(int)

    if "diamonds" in df.columns and "boxes" in df.columns:
        df["diam_box_ratio"] = df["diamonds"] / df["boxes"].replace(0, np.nan)
        df["rm_group"] = df["diam_box_ratio"].round(1)

    df["overhead_ratio"] = df["translation_time"] / (df["z3_time"] + 0.0001)

    return df


# ===================================================================
# HELPERS
# ===================================================================

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
    """
    Interpolates the ratio where P(SAT) crosses 0.5.
    """
    xs = frac.index.to_numpy()
    ys = frac.values

    if 0.5 in ys:
        return xs[list(ys).index(0.5)]

    for i in range(len(xs) - 1):
        if ys[i] >= 0.5 and ys[i + 1] <= 0.5:
            t = (0.5 - ys[i]) / (ys[i + 1] - ys[i])
            return xs[i] + t * (xs[i + 1] - xs[i])
    return None


def get_sat_fraction(df):
    return (
        df.groupby("ratio")["result"].apply(lambda r: (r == "SAT").mean()).sort_index()
    )


def get_median_time(df, column):
    return df.groupby("ratio")[column].median().sort_index()


def prepare_world_buckets(decided):
    decided_w = decided.copy()

    if decided_w.empty:
        return decided_w, []

    max_worlds = int(decided_w["worlds"].max())
    max_worlds = max(max_worlds, 100)
    bins = list(range(0, max_worlds + 200, 100))
    labels = [f"{bins[i]}-{bins[i + 1]}" for i in range(len(bins) - 1)]
    decided_w["w_bucket"] = pd.cut(decided_w["worlds"], bins=bins, labels=labels)
    active_buckets = sorted(
        decided_w["w_bucket"].dropna().unique(), key=lambda x: labels.index(x)
    )

    return decided_w, active_buckets


# ===================================================================
# T1: TRANSITION CURVE SAT/UNSAT
# ===================================================================


def plot_t1(decided_w, active_buckets, rm_groups):

    if not active_buckets:
        return

    ncols = min(3, len(active_buckets))
    nrows = int(np.ceil(len(active_buckets) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows), sharey=True)
    axes = np.atleast_1d(axes).ravel()

    for ax, bucket in zip(axes, active_buckets):
        sub_df = decided_w[decided_w["w_bucket"] == bucket]

        for idx, rm in enumerate(rm_groups):
            st = style_for(idx)
            rm_df = sub_df[sub_df["rm_group"] == rm]
            frac = get_sat_fraction(rm_df)

            if len(frac) <= 1:
                continue

            ax.plot(
                frac.index,
                frac.values,
                marker=st["marker"],
                linestyle=st["linestyle"],
                color=st["color"],
                linewidth=1.8,
                label=f"Diam/Cajas = {rm}",
            )
            threshold = interpolate_threshold(frac)

            if threshold is not None:
                ax.axvline(
                    threshold,
                    color=st["color"],
                    linestyle=":",
                    linewidth=1.5,
                    alpha=0.7,
                )

        ax.axhline(0.5, color="black", linestyle="--", linewidth=1)
        ax.set_title(f"Worlds {bucket}")
        ax.set_xlabel("Propositional Density (Ratio M/N)")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=8)

    for ax in axes[len(active_buckets) :]:
        ax.set_visible(False)

    axes[0].set_ylabel("Probability of being SAT (P(SAT))")
    fig.suptitle(
        "T1: Transition curve SAT/UNSAT for amount of worlds", fontsize=14
    )
    plt.tight_layout()


# ===================================================================
# T2: DIFFICULTY CURVE
# ===================================================================
def plot_t2(decided_w, world_panels, rm_groups, time_column, title, ylabel):

    if not world_panels:
        return

    fig, axes = plt.subplots(
        1, len(world_panels), figsize=(5 * len(world_panels), 5), sharey=True
    )

    if len(world_panels) == 1:
        axes = [axes]

    for ax, bucket in zip(axes, world_panels):
        sub_df = decided_w[decided_w["w_bucket"] == bucket]
        for idx, rm in enumerate(rm_groups):
            st = style_for(idx)
            rm_df = sub_df[sub_df["rm_group"] == rm]
            med = get_median_time(rm_df, time_column)

            if len(med) <= 1:
                continue

            ax.plot(
                med.index,
                med.values,
                marker=st["marker"],
                linestyle=st["linestyle"],
                color=st["color"],
                label=f"Diam/Boxes = {rm}",
            )
            frac = get_sat_fraction(rm_df)
            threshold = interpolate_threshold(frac)

            if threshold is not None:
                ax.axvline(
                    threshold,
                    color=st["color"],
                    linestyle=":",
                    linewidth=1.5,
                    alpha=0.7,
                )
        ax.set_title(f"Worlds {bucket}")
        ax.set_xlabel("Propositional Ratio (M/N)")
        ax.set_yscale("log")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", fontsize=8)

    axes[0].set_ylabel(ylabel)
    fig.suptitle(title)
    plt.tight_layout()


# ===================================================================
# T3: BEllS BY SIZE OF MODEL
# ===================================================================
def plot_t3(decided_w, active_buckets, time_column, title):

    plt.figure(figsize=(11, 6))
    for idx, bucket in enumerate(active_buckets):
        st = style_for(idx)
        sub_df = decided_w[decided_w["w_bucket"] == bucket]
        med = get_median_time(sub_df, time_column)
        frac = get_sat_fraction(sub_df)

        if len(med) <= 1:
            continue

        plt.plot(
            med.index,
            med.values,
            marker=st["marker"],
            linestyle="-",
            linewidth=2,
            color=st["color"],
            label=str(bucket),
        )

        threshold = interpolate_threshold(frac)

        if threshold is not None:
            plt.axvline(
                threshold, color=st["color"], linestyle=":", linewidth=2, alpha=0.8
            )

    plt.xlabel("Propositional Density (Ratio M/N)")
    if time_column == "z3_time":
        plt.ylabel("Median Time (Z3, s)")
    else:
        plt.ylabel("Median Time (TOTAL, s)")
    plt.yscale("log")
    plt.title(title)
    plt.legend(title="Real Worlds", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()


# ===================================================================
# T5: MOUNTAIN 3D
# ===================================================================
def plot_t5(decided_w, active_buckets, time_column, title, zlabel):

    if not active_buckets:
        return

    ncols = min(3, max(1, len(active_buckets)))
    nrows = max(1, int(np.ceil(len(active_buckets) / ncols)))
    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=(5 * ncols, 4 * nrows),
        subplot_kw={"projection": "3d"},
    )
    axes = np.atleast_1d(axes).ravel()
    cmap = plt.get_cmap("coolwarm")
    for ax, bucket in zip(axes, active_buckets):
        sub_df = decided_w[decided_w["w_bucket"] == bucket]

        if sub_df.empty or pd.isna(sub_df[time_column].max()):
            ax.set_visible(False)
            continue

        max_time_local = sub_df[time_column].max()
        for rm_val in sorted(sub_df["rm_group"].dropna().unique()):
            rm_df = sub_df[sub_df["rm_group"] == rm_val]
            grouped = rm_df.groupby("ratio")[time_column].median().sort_index()

            if len(grouped) <= 1:
                continue

            xs = grouped.index.to_numpy()
            zs = grouped.values
            ys = np.full_like(xs, rm_val)

            if max_time_local > 0:
                normalized = np.clip(zs.max() / max_time_local, 0, 1)
            else:
                normalized = 0

            color_val = cmap(normalized)
            ax.plot(xs, ys, zs, color=color_val, linewidth=2.5, alpha=0.9)
            ax.scatter(
                xs, ys, zs, color=color_val, s=20, edgecolors="white", linewidth=0.5
            )

        ax.set_title(f"{bucket}")
        ax.set_xlabel("Ratio M/N", labelpad=8)
        ax.set_ylabel("Diam/Boxes", labelpad=8)
        ax.set_zlabel(zlabel, labelpad=8)
        ax.view_init(elev=25, azim=135)

    for ax in axes[len(active_buckets) :]:
        ax.set_visible(False)

    fig.suptitle(title)
    plt.tight_layout()


# ===================================================================
# T6: PHASE TRANSITION EQUATION
# ===================================================================
def plot_t6(decided_w, active_buckets):

    plt.figure(figsize=(10, 6))
    x_worlds = []
    y_thresholds = []

    for bucket in active_buckets:
        sub_df = decided_w[decided_w["w_bucket"] == bucket]

        if sub_df.empty:
            continue

        frac = get_sat_fraction(sub_df)
        threshold = interpolate_threshold(frac)

        if threshold is not None:
            x_worlds.append(sub_df["worlds"].mean())
            y_thresholds.append(threshold)

    if len(x_worlds) <= 1:
        return None, None

    plt.scatter(
        x_worlds,
        y_thresholds,
        color="red",
        s=100,
        zorder=5,
        edgecolors="black",
        label="Empirical Thresholds",
    )

    coefs = np.polyfit(x_worlds, y_thresholds, 1)
    m_coef, b_coef = coefs
    r_squared = np.corrcoef(x_worlds, y_thresholds)[0, 1] ** 2
    x_line = np.linspace(min(x_worlds) * 0.8, max(x_worlds) * 1.1, 100)

    plt.plot(
        x_line,
        m_coef * x_line + b_coef,
        color="blue",
        linestyle="--",
        linewidth=2,
        label=(
            f"Linear Fit "
            f"($R^2={r_squared:.2f}$)\n"
            f"$Ratio = {m_coef:.4f}"
            f"\\times W + {b_coef:.2f}$"
        ),
    )

    plt.xlabel("Average number of worlds ($W$)")
    plt.ylabel("Critical Ratio " "(Threshold $P(SAT) = 0.5$)")
    plt.title("T6: Mathematical Relationship Between Worlds and Phase Transition")
    plt.legend()
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    return m_coef, b_coef, r_squared


# ===================================================================
# G1: DISPERSION
# ===================================================================
def plot_g1(df):

    plt.figure(figsize=(10, 6))
    sat_df = df[df["result"] == "SAT"]
    unsat_df = df[df["result"] == "UNSAT"]
    plt.scatter(
        sat_df["z3_time"],
        sat_df["translation_time"],
        c="blue",
        alpha=0.6,
        label="SAT",
        edgecolor="k",
    )
    plt.scatter(
        unsat_df["z3_time"],
        unsat_df["translation_time"],
        c="red",
        alpha=0.6,
        label="UNSAT",
        edgecolor="k",
        marker="s",
    )
    plt.xlabel("Time of Z3 (segundos)")
    plt.ylabel("Time of translate on Python (seconds)")
    plt.title("G1: Bottleneck (Translate vs Resolution)")
    plt.axvline(
        x=df["z3_time"].median(),
        color="gray",
        linestyle="--",
        alpha=0.7,
        label="Median Z3",
    )
    plt.legend()
    plt.grid(True, alpha=0.3)


# ===================================================================
# G2: SCALING BY SIZE
# ===================================================================
def plot_g2(df):
    plt.figure(figsize=(10, 6))
    df_sorted = df.sort_values("size")
    window = max(1, len(df_sorted) // 20)
    plt.plot(
        df_sorted["size"] / 1024,
        df_sorted["translation_time"].rolling(window).mean(),
        color="purple",
        linewidth=3,
        label="Time of Translate (Trend)",
    )
    plt.plot(
        df_sorted["size"] / 1024,
        df_sorted["z3_time"].rolling(window).mean(),
        color="green",
        linewidth=3,
        label="Time of Z3 (Trend)",
    )
    plt.xlabel("Formula Size in KB (Memory Friction)")
    plt.ylabel("Average Time (seconds)")
    plt.title("G2: Time Scaling Based on Formula Weight")
    plt.legend()
    plt.grid(True, alpha=0.3)


# ===================================================================
# G3: DIAMONDS VS BOXES
# ===================================================================
def plot_g3(df):

    plt.figure(figsize=(14, 6))

    world_data = []
    world_values = sorted(df["diamonds"].dropna().unique())

    for value in world_values:
        values = df[df["diamonds"] == value]["translation_time"].dropna()
        world_data.append(values)

    plt.boxplot(world_data, tick_labels=[str(int(x)) for x in world_values])

    # Add median above each boxplot
    for i, values in enumerate(world_data, start=1):

        if len(values) == 0:
            continue

        median = values.median()
        plt.text(
            i, median + 1.5, f"{median:.2f} s", ha="center", va="bottom", fontsize=10
        )

    plt.xlabel("Amount Diamonds")
    plt.ylabel("Time of translate (seconds)")
    plt.title("G3A: Translation Time Based on Modal Size")
    plt.grid(True, axis="y", alpha=0.3)

    plt.suptitle("G3: Impact of Modal Operators on the Parser")
    plt.tight_layout()


# ===================================================================
# G4: IMPACT OF RATIOS
# ===================================================================
def plot_g4(df):

    df_plot_modal = df[df["modal_ratio"] < 900]
    plt.figure(figsize=(14, 6))

    # G4A
    plt.scatter(
        df["ratio"],
        df["translation_time"],
        color="purple",
        alpha=0.5,
        edgecolor="k",
        label="Translate",
    )

    plt.scatter(
        df["ratio"], df["z3_time"], color="green", alpha=0.5, edgecolor="k", label="Z3"
    )
    plt.xlabel("Propositional Ratio (m/n)")
    plt.ylabel("Time (s)")
    plt.title("G4A: Impact by Propositional Ratio")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()


# ===================================================================
# CONSOLE REPORT
# ===================================================================
def print_report(df, n_values, x_worlds, m_coef, b_coef, r_squared):

    print("\n" + "=" * 80)
    print("=== MEGA-REPORT: ANATOMY Z3 AND BOTTLENECKS ===")
    print("=" * 80)

    for n in n_values:
        n_df = df[(df["n"] == n) & (df["result"] != "TO")].copy()

        if n_df.empty:
            continue

        print(f"\n--- RESULTS OF Z3 FOR n = {n} ---")

        grouped = (
            n_df.groupby("ratio")
            .agg(
                median_time=("z3_time", "median"),
                avg_boxes=("boxes", "mean"),
                avg_diamonds=("diamonds", "mean"),
            )
            .reset_index()
        )

        peak = grouped.loc[grouped["median_time"].idxmax()]

        print(
            f" Central Peack -> "
            f"Critical Ratio: {peak['ratio']:.2f} | "
            f"Time Z3: {peak['median_time']:.4f} s "
            f"(Diam: {peak['avg_diamonds']:.0f}, "
            f"Boxes: {peak['avg_boxes']:.0f})"
        )

    if len(x_worlds) > 1:
        print(
            f"\n[ EQUATION S5 ] "
            f"r = {m_coef:.4f} * W + "
            f"{b_coef:.4f} "
            f"(R2={r_squared:.4f})"
        )

    print("\n--- Bottleneck Correlations (1.0 = direct impact) ---")

    columnas_corr = [
        "size",
        "m",
        "ratio",
        "worlds",
        "diamonds",
        "boxes",
        "modal_ratio",
        "translation_time",
        "z3_time",
        "time",
    ]

    correlaciones = df[columnas_corr].corr()

    print("Factors that destroy Python memory " "(Translate):")

    for index, value in (
        correlaciones["translation_time"]
        .drop(["translation_time", "z3_time", "time"])
        .items()
    ):

        print(f"  - {index.ljust(15)}: " f"{value:.3f}")

    print("\nFactors that destroy Python memory " "(Z3):")

    for index, value in (
        correlaciones["z3_time"].drop(["translation_time", "z3_time", "time"]).items()
    ):

        print(f"  - {index.ljust(15)}: " f"{value:.3f}")

    print("\n" + "=" * 80)
    print("=== TOP 30 FORMULAS WITH THE WORST BOTTLENECKS ===")
    print("=" * 80)

    top_ineficientes = df.sort_values("overhead_ratio", ascending=False).head(30)

    columnas_mostrar = [
        "worlds",
        "ratio",
        "modal_ratio",
        "m",
        "diamonds",
        "boxes",
        "size",
        "translation_time",
        "z3_time",
        "time",
        "result",
    ]

    print(top_ineficientes[columnas_mostrar].to_string(index=False))


# ===================================================================
# MAIN
# ===================================================================
def main():

    parser = argparse.ArgumentParser(
        description=("S5 Advanced Analyzer: " "Z3 vs Total Time + Bottlecuts.")
    )

    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help=("Include CSVs from " "'other_batchs/'."),
    )

    args = parser.parse_args()

    # ---------------------------------------------------------------
    # Load data
    # ---------------------------------------------------------------

    df = load_data(include_other=args.all)

    if df is None:
        print("Doesn't found valid CSV files.")
        sys.exit(1)

    # ---------------------------------------------------------------
    # Clean data
    # ---------------------------------------------------------------

    df = clean_data(df)

    n_values = sorted(df["n"].unique())

    # ---------------------------------------------------------------
    # Data main
    # ---------------------------------------------------------------

    n_target = max(n_values)
    n_df = df[df["n"] == n_target].copy()
    decided = n_df[n_df["result"] != "TO"].copy()
    rm_groups = sorted(decided["rm_group"].dropna().unique())
    decided_w, active_buckets = prepare_world_buckets(decided)
    world_panels = active_buckets[:3]

    # ---------------------------------------------------------------
    # T1
    # ---------------------------------------------------------------
    plot_t1(decided_w, active_buckets, rm_groups)

    # ---------------------------------------------------------------
    # T2 Z3
    # ---------------------------------------------------------------
    plot_t2(
        decided_w,
        world_panels,
        rm_groups,
        "z3_time",
        "T2-Z3: Z3 difficulty by world and modal relationship",
        "Median Time (Z3, s)",
    )

    # ---------------------------------------------------------------
    # T3 Z3
    # ---------------------------------------------------------------
    plot_t3(
        decided_w, active_buckets, "z3_time", "T3-Z3: Bells and Thresholds (Z3 Time)"
    )

    # ---------------------------------------------------------------
    # T5 Z3
    # ---------------------------------------------------------------
    plot_t5(
        decided_w,
        active_buckets,
        "z3_time",
        "T5-Z3: Complexity of mountain 3D (Z3 Time)",
        "Median (Z3, s)",
    )

    # ---------------------------------------------------------------
    # T6
    # ---------------------------------------------------------------
    result_t6 = plot_t6(decided_w, active_buckets)
    if result_t6[0] is not None:
        m_coef, b_coef, r_squared = result_t6
        # Data recovered for report
        x_worlds = []
        y_thresholds = []
        for bucket in active_buckets:
            sub_df = decided_w[decided_w["w_bucket"] == bucket]
            if sub_df.empty:
                continue
            frac = get_sat_fraction(sub_df)
            threshold = interpolate_threshold(frac)
            if threshold is not None:
                x_worlds.append(sub_df["worlds"].mean())
                y_thresholds.append(threshold)
    else:
        x_worlds = []
        m_coef = None
        b_coef = None
        r_squared = None

    # ---------------------------------------------------------------
    # T2 TOTAL
    # ---------------------------------------------------------------
    plot_t2(
        decided_w,
        world_panels,
        rm_groups,
        "time",
        "T2-TOTAL: Difficulty (including overhead of Python)",
        "Median Time (TOTAL, s)",
    )

    # ---------------------------------------------------------------
    # T3 TOTAL
    # ---------------------------------------------------------------
    plot_t3(
        decided_w,
        active_buckets,
        "time",
        "T3-TOTAL: Bells Deformed by the Parser (Total Time)",
    )

    # ---------------------------------------------------------------
    # T5 TOTAL
    # ---------------------------------------------------------------
    plot_t5(
        decided_w,
        active_buckets,
        "time",
        "T5-TOTAL: Mountain 3D (Z3 + Python Overhead)",
        "Median (TOTAL, s)",
    )
    plot_g1(df)
    plot_g2(df)
    plot_g3(df)
    plot_g4(df)
    plt.show()

    print_report(df, n_values, x_worlds, m_coef, b_coef, r_squared)


if __name__ == "__main__":
    main()
