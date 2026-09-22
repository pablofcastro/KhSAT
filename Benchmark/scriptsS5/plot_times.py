import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import os

# 1. Cargar y combinar todos los CSVs
archivos_csv = glob.glob("tiempos_comparacion/output-batch*.csv")

if not archivos_csv:
    print("No se encontraron archivos CSV en la carpeta 'tiempos_comparacion'.")
    exit()

df = pd.concat([pd.read_csv(archivo) for archivo in archivos_csv], ignore_index=True)

# 2. Limpiar datos (quedarnos solo con SAT y UNSAT)
df = df.dropna(subset=['result'])
df = df[df['result'].isin(['SAT', 'UNSAT'])]

# 3. Transformar el DataFrame para enfocar solo en las fases ANTES de Z3
# Tomamos parse_time, nnf_time y tosat_time
df_pre_z3 = df.melt(
    id_vars=['ratio', 'modal_ratio', 'worlds', 'result'], 
    value_vars=['parse_time', 'nnf_time', 'tosat_time'],
    var_name='Fase_Traduccion', 
    value_name='Tiempo'
)

# Renombrar para que los gráficos sean más legibles
df_pre_z3['Fase_Traduccion'] = df_pre_z3['Fase_Traduccion'].replace({
    'parse_time': '1. Parseo (String -> AST)', 
    'nnf_time': '2. Conversión a NNF',
    'tosat_time': '3. Traducción a Lógica Proposicional'
})

# Configuración visual
sns.set_theme(style="whitegrid")
paleta_fases = {'1. Parseo (String -> AST)': '#4C72B0', '2. Conversión a NNF': '#DD8452', '3. Traducción a Lógica Proposicional': '#C44E52'}


# ==========================================
# GRÁFICO 1: Fases Pre-Z3 vs Ratio Proposicional (m/n)
# ==========================================
g1 = sns.relplot(
    data=df_pre_z3, 
    x='ratio', 
    y='Tiempo', 
    hue='Fase_Traduccion', 
    col='result',    
    kind='line',       # Cambiamos a línea para ver la tendencia de crecimiento
    marker='o',
    palette=paleta_fases, 
    height=5, 
    aspect=1.2,
    errorbar=None      # Quita las bandas de error para mayor claridad visual
)
g1.fig.suptitle('Desglose de Traducción vs Ratio (m/n)', y=1.05, fontsize=14)
g1.set_titles("Resultado Final: {col_name}")
g1.set_axis_labels("Ratio Proposicional (m/n)", "Tiempo (segundos)")
plt.show()

# ==========================================
# GRÁFICO 2: Fases Pre-Z3 vs Ratio Modal (Diamantes/Cajas)
# ==========================================
df_modal = df_pre_z3[df_pre_z3['modal_ratio'] < 900]

g2 = sns.relplot(
    data=df_modal, 
    x='modal_ratio', 
    y='Tiempo', 
    hue='Fase_Traduccion', 
    col='result',
    kind='scatter',    # Mantenemos scatter aquí porque el ratio modal suele ser más disperso
    palette=paleta_fases, 
    s=100, 
    alpha=0.8,
    height=5, 
    aspect=1.2
)
g2.fig.suptitle('Desglose de Traducción vs Ratio Modal', y=1.05, fontsize=14)
g2.set_titles("Resultado Final: {col_name}")
g2.set_axis_labels("Ratio Modal (Diamantes/Cajas)", "Tiempo (segundos)")
plt.show()

# ==========================================
# GRÁFICO 3: Fases Pre-Z3 vs Cantidad de Mundos
# ==========================================
g3 = sns.relplot(
    data=df_pre_z3, 
    x='worlds', 
    y='Tiempo', 
    hue='Fase_Traduccion', 
    col='result',
    kind='line',       # Usamos línea para ver cómo escala con el número de mundos
    marker='s',        # 's' para cuadrados en vez de círculos
    palette=paleta_fases, 
    height=5, 
    aspect=1.2,
    errorbar=None
)
g3.fig.suptitle('Impacto de la Cantidad de Mundos en cada Fase de Traducción', y=1.05, fontsize=14)
g3.set_titles("Resultado Final: {col_name}")
g3.set_axis_labels("Cantidad de Mundos Generados", "Tiempo (segundos)")
plt.show()