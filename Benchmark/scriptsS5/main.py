import sys
import os
import s5

benchmark_size = 10 # 10 instancias por configuración es suficiente para estadísticas robustas
benchmark_path = "../formulasS5/"

if __name__ == '__main__':
    os.makedirs(benchmark_path, exist_ok=True)
    
    n = 120
    l = 3
    
    # =========================================================
    # CÓMO DIVIDIRSE EL TRABAJO:
    # Amigo 1 usa: D_values = range(600, 1001, 100)  (600 a 1000)
    # Amigo 2 usa: D_values = range(1100, 1501, 100) (1100 a 1500)
    # =========================================================
    D_values = range(600, 1501, 100) 
    
    # Ratio Modal (Diamantes / Cajas)
    modal_ratios = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    
    # Ratios (M/N) con foco entre 6 y 12
    ratios = [2.0, 4.0, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 10.0, 11.0, 12.0, 14.0]

    print("Iniciando generación masiva REANUDABLE...")
    generadas = 0
    omitidas = 0
    imposibles = 0
    
    for D in D_values:
        for Rm in modal_ratios:
            B = int(D / Rm) # Si Rm = D/B, entonces B = D/Rm
            
            for r in ratios:
                m = int(n * r)
                
                # Control físico: Si piden más operadores que literales totales, la saltamos.
                if (D + B) > (m * l):
                    imposibles += 1
                    continue
                    
                for i in range(1, benchmark_size + 1):
                    # Nomenclatura: formula{id}-{n}-{m}-{l}-{D}-{B}.s5
                    fname = os.path.join(benchmark_path, f"formula{i}-{n}-{m}-{l}-{D}-{B}.s5")
                    
                    # REANUDABLE: Si el archivo ya existe, lo saltamos instantáneamente
                    if os.path.exists(fname):
                        omitidas += 1
                        continue
                        
                    try:
                        formula_str = s5.phi(n, m, l, D, B)
                        with open(fname, 'w') as ffile:
                            ffile.write(formula_str)
                        generadas += 1
                        print(f"Generada: {fname} | Diam/Cajas: {Rm}")
                    except Exception as e:
                        print(f"Error en {fname}: {e}")
                        
    print(f"\nGeneración finalizada.")
    print(f"Nuevas: {generadas} | Omitidas (ya existían): {omitidas} | Imposibles matemáticamente: {imposibles}")