import s5
# Generar una formula dificil: 
# 10 variables, 40 clausulas, tamaño 3 (3-SAT modal), 60% modales
formula_dificil = s5.phi(n=10, m=40, l=3, p=0.6)
print(formula_dificil)