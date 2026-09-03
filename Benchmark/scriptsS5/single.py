import os
import s5

if __name__ == '__main__':

    # 1. Params for formula
    W_target = 1100
    n = 120
    l = 3
    Rm = 1.0

    # Ratio propositional predicted with a linear regression
    predicted_ratio = 0.0050 * W_target + 4.25
    
    m = int(n * predicted_ratio)
    D = W_target + 10
    B = int(D / Rm)

    # 3. Test validation
    print("=== Tes validation 60s ===")
    print(f"Worlds (W): {W_target}")
    print(f"Ratio Propositional predicted: {predicted_ratio}")
    print(f"Clauses (m): {m}")
    print(f"Diamonds (D): {D}")
    print(f"Boxes (B): {B}")
    
    total_gaps = m * l
    total_operators = D + B
    print(f"Total Gaps: {total_gaps}")
    print(f"Total operators to insert: {total_operators}")
    
    if (W_target - 1) > m or total_operators > total_gaps:
        print("ERROR: The formula does not fit in the physical space. Raise 'l' to 4.")
        exit(1)
    else:
        print("STATE: Viable. Remaining space:", total_gaps - total_operators, "gaps.")

    # 4. Generation
    fname = f"formula-teoria-60s-W{W_target}.s5"
    print(f"\nGenerating {fname}...")
    
    try:
        formula_str = s5.phi(n, m, l, D, B, W_target)
        
        with open(fname, 'w') as ffile:
            ffile.write(formula_str)
            
        print(f"¡Fórmula created sussesfully! Size: {os.path.getsize(fname)} bytes.")
        print(f"Command suggested: python3 ../../s5_solver.py -f {fname}")
        
    except Exception as e:
        print(f"Error to generate formula: {e}")