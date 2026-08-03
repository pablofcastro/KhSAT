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
    Genera una fórmula S5 aleatoria en formato CNF usando el método New K-CNF.
    
    n: Número de variables proposicionales disponibles (N)
    m: Número total de cláusulas (L en el paper)
    L: Tamaño de cada cláusula (K)
    P: Proporción de literales puramente proposicionales en cada cláusula (p)
    """
    
    r = ""

    for _ in range(m):
        
        r+= clause(n,l,p) + " & "
    
    return r[:-3]  
            
    
    
    