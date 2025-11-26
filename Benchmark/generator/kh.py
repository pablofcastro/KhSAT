def khplus(n:int):
    
    r = ""

    for i in range(n):
        r += f"kh(p{i},p{i+1});"

    return r

def khminus(n:int):
    
    r = ""

    for i in range(n):
        r += f"~kh(q0{i},q1{i});"

    return r

def khsabotage(s:list[tuple[int,int]]):
    r = ""

    for i in range(len(s)):

        r += f"~kh(p{s[i][0]},p{s[i][1]});"

    return r

def phi(n:int, m:int, s:list[tuple[int,int]]):
    
    return khplus(n)+khminus(m)+khsabotage(s)