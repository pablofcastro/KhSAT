import random

diamonds_generated = 0
# W = MAX_DIAMONS + 1
MAX_DIAMONDS = 100000000

def random_var(n):
    return f"p{random.randint(0,n-1)}"

def literal(n, p):
    global diamonds_generated
    lit = random_var(n)

    if random.random() < 0.5:
        lit = f"~{lit}"
        
    if random.random() < p:

        if diamonds_generated < MAX_DIAMONDS:
            op = random.choice(["A", "E"])
            if op == "E":
                diamonds_generated += 1
        else:
            op = "A"
            
        lit = f"{op} {lit}"
        

        
    return lit
 
def clause(n,l,p):
    
    r = "("
    
    for _ in range(l):
    
        r += literal(n,p) + " | "
    
    return r[:-3] + ")" 
    

def phi(n ,m ,l ,p):

    """
    Generate fórmula S5 random in CNF format using the New K-CNF method.
    
    n: Number of propositional variables available (N)
    m: Total number of clauses (L in the paper)
    L: Size of each clause (K)
    P: Proportion of purely propositional literals in each clause (p)
    """
    
    global diamonds_generated
    # ¡ESTO ES CRÍTICO! Reiniciamos los mundos para CADA fórmula nueva
    diamonds_generated = 0
        
    r = ""

    for _ in range(m):
        
        r+= clause(n,l,p) + " & "
    
    return r[:-3]  
            
