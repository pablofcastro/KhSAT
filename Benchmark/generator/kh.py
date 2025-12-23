import random

def khplus(n, k):
    r = ""
    indexes_pre = [random.randint(0, k) for _ in range(n)]
    indexes_post = [random.randint(0, k) for _ in range(n)]
    for i,j in zip(indexes_pre,indexes_post) :
            r += f"Kh(p{i},p{j});"

    return r

def khminus(n, k):
    
    r = ""
    indexes_pre = [random.randint(0, k) for _ in range(n)]
    indexes_post = [random.randint(0, k) for _ in range(n)]
    for i,j in zip(indexes_pre, indexes_post) :
            r += f"~Kh(p{i},p{j});"

    return r

def khsabotage(s:list[tuple[int,int]]):
    r = ""

    for i in range(len(s)):

        r += f"~Kh(p{s[i][0]},p{s[i][1]});"

    return r

def phi(n, m, k, s=[]):
    #formula = khplus(n)+khminus(m)+khsabotage(s)
    formula = khplus(n, k)+khminus(m, k)#+khsabotage(s)
    return formula[:-1] # last semicolon removed