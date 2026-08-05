import random

def random_var(n):
    return f"p{random.randint(0,n-1)}"

def literal(n, p):

    lit= random_var(n)

    if random.random() < 0.5:
        lit = f"~{lit}"
        
    if random.random() < p:
        op = random.choice(["A","E"])
        lit = f"{op} {lit}"
        
        if random.random() < 0.5:
            op2 = random.choice(["A","E"])
            lit = f"{op2}({lit})"
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
    
    r = ""

    for _ in range(m):
        
        r+= clause(n,l,p) + " & "
    
    return r[:-3]  
            
