import os

path_interesting_formulas = os.path.join(os.path.dirname(__file__), '..', 'interesting_formulas')

#positive atom
def kh_pos(i):
  return f"Kh(p{i},p{i+1})"

#negative atom
def kh_neg(m):
  return f"~Kh(p0,p{m})"

def create_interesting_formulas(m):
    formula_name = f"formula{m}-{m}-1.kh"
    file = os.path.join(path_interesting_formulas, formula_name)

    interesting_formula = ""

    for i in range (0, m):
        interesting_formula = interesting_formula + kh_pos(i) + ";"

    interesting_formula = interesting_formula + kh_neg(m)

    with open(file, "w") as f:
        f.write(interesting_formula) 


if __name__ == "__main__" :
   create_interesting_formulas(3)
   for m in range (1, 50):  
      create_interesting_formulas(m)