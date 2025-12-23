import pandas as pd
import matplotlib.pyplot as plt
import glob
from mpl_toolkits.mplot3d import Axes3D

# ---- Load multiple CSV files ----
# Adjust the folder path as needed (e.g., "./data/*.csv")
file_list = ["output-batch1.csv", "output-batch2.csv", "output-batch3.csv", "output-batch4.csv", "output-batch5.csv"]

dfs = [pd.read_csv(f) for f in file_list]
df = pd.concat(dfs, ignore_index=True)

# ---- Clean result column (e.g., 'SAT.' -> 'SAT') ----
df["result"] = df["result"].str.replace(".", "", regex=False)

df_sat = df[df["result"] == "SAT"]
df_unsat = df[df["result"] == "UNSAT"]
df_to = df[df["result"] == "TO"]       # ← timeouts

# ---- 3D Plot ----
fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")
ax.view_init(elev=35, azim=45)

# SAT = blue dots
ax.scatter(df_sat["neg"], df_sat["pos"], df_sat["time"],
           c="blue", marker="o", label="SAT", alpha=0.5)

# UNSAT = red dots
ax.scatter(df_unsat["neg"], df_unsat["pos"], df_unsat["time"],
           c="red", marker="o", label="UNSAT", alpha=0.5)

# TO = black dots
ax.scatter(df_to["neg"], df_to["pos"], df_to["time"],
           c="black", marker="o", label="TO", alpha=0.5)

# ---- Labels ----
ax.set_xlabel("neg")
ax.set_ylabel("pos")
ax.set_zlabel("time")

ax.legend()
ax.legend(bbox_to_anchor=(1.27, 0.7), loc="upper right")

plt.show()