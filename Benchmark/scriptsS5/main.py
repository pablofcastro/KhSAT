import sys
import os
import s5

benchmark_size = 10 # 10 por configuración es un buen balance entre rigor y tiempo
benchmark_path = "../formulasS5/"

if __name__ == '__main__':
    os.makedirs(benchmark_path, exist_ok=True)
    
    n = 120
    l = 3
    
    # 1. MUNDOS A PROBAR (Con dos valores probamos el salto estructural)
# 1. MUNDOS A PROBAR (Los Pesos Pesados)
    # 800 y 1000 mundos obligarán a Z3 a construir un modelo masivo en memoria.
    W_values = [800, 1000] 
    
    # 2. RATIOS MODALES (Diamantes / Cajas)
    # Centrados exactamente en el punto de máxima fricción (1.0). 
    # Añadimos 0.8 y 1.2 para ver cómo la campana se inclina hacia los lados.
    modal_ratios = [0.9, 1.0, 1.1]
    
    # 3. RATIOS PROPOSICIONALES (M/N)
    # Lo desplazamos hacia la derecha. Recuerda que para 1000 mundos, 
    # los ratios menores a 8.5 son físicamente imposibles, así que el script 
    # los saltará automáticamente y se concentrará en la zona útil.
    ratios = [7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12]

    print("Iniciando generación con Mundos Fijos y Ratios Modales precisos...")
    generadas = 0
    omitidas = 0
    imposibles = 0
    
    for W_target in W_values:
        # Añadimos unos pocos diamantes extra (10) por encima del mínimo exigido por W
        # Esto permite que haya un poco de "ruido" natural en las cláusulas.
        D = W_target + 10 
        
        for Rm in modal_ratios:
            # Calculamos las cajas para lograr la relación modal (Diamantes/Cajas)
            B = int(D / Rm) 
            
            for r in ratios:
                m = int(n * r)
                
                # --- CONTROLES DE FÍSICA MATEMÁTICA ---
                # 1. ¿Hay suficientes cláusulas para crear los mundos?
                if (W_target - 1) > m:
                    imposibles += 1
                    continue 
                # 2. ¿Hay suficientes huecos para meter todos los operadores?
                if (D + B) > (m * l):
                    imposibles += 1
                    continue 
                    
                for i in range(1, benchmark_size + 1):
                    # Mantengo el nombre original para no romper tu lector de CSV
                    fname = os.path.join(benchmark_path, f"formula{i}-{n}-{m}-{l}-{D}-{B}.s5")
                    
                    if os.path.exists(fname):
                        omitidas += 1
                        continue
                        
                    try:
                        # Asegúrate de usar el s5.phi que acepta W_target al final
                        formula_str = s5.phi(n, m, l, D, B, W_target)
                        with open(fname, 'w') as ffile:
                            ffile.write(formula_str)
                        generadas += 1
                        print(f"Generada: {fname} | Mundos: {W_target} | Diam/Cajas: {Rm} | Ratio: {r}")
                    except Exception as e:
                        print(f"Error en {fname}: {e}")
                        
    print(f"\nGeneración finalizada.")
    print(f"Nuevas: {generadas} | Omitidas: {omitidas} | Imposibles: {imposibles}")