import sys
import os
import s5

benchmark_size = 10 
benchmark_path = "../formulasS5/"

if __name__ == '__main__':
    os.makedirs(benchmark_path, exist_ok=True)
    
    n_values = [120]
    l = 3
    
    # 1. Worlds for test
    W_values = [400, 600, 1000]
    
    # 2. RATIO MODAL
    modal_ratios = [ 0.7, 0.8, 0.9, 1.0, 1.1]

    generated = 0
    omited = 0
    impossible = 0
    
    for n in n_values:
        for W_target in W_values:
            D = W_target + 10 

            predicted_ratio = 0.0050 * W_target + 4.25
            # Create a larger window around the predicted peak to encompass more ratios
            r_min = max(4.0, round(predicted_ratio - 5.0, 1))
            r_max = round(predicted_ratio + 5.0, 1)

            ratios = []
            r = r_min
            while r <= r_max + 0.1:
                ratios.append(round(r, 1))
                r += 0.5
                
            print(f"-> For W={W_target}, the predicted ratio is {predicted_ratio:.2f}. Exploring only: {ratios}")
            
            for Rm in modal_ratios:
                B = int(D / Rm) 
                
                for r in ratios:
                    m = int(n * r)
                    
                    if (W_target - 1) > m or (D + B) > (m * l):
                        impossible += 1
                        continue 
                        
                    for i in range(1, benchmark_size + 1):
                        fname = os.path.join(benchmark_path, f"formula{i}-{n}-{m}-{l}-{D}-{B}.s5")
                        
                        if os.path.exists(fname):
                            omited += 1
                            continue
                            
                        try:
                            formula_str = s5.phi(n, m, l, D, B, W_target)
                            with open(fname, 'w') as ffile:
                                ffile.write(formula_str)
                            generated += 1
                        except Exception as e:
                            print(f"Error en {fname}: {e}")
                            
    print(f"\nGeneración finalizada.")
    print(f"Nuevas: {generated} | omited: {omited} | impossible: {impossible}")