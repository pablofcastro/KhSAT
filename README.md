# Project Name

A SAT solver for the logics S5 and Knowing-How logic.

The algorithm for S5 is based on the paper:

*Thomas Caridroit, Jean-Marie Lagniez, Daniel Le Berre, Tiago de Lima, Valentin Montmirail.  A SAT Based Approach for Solving the Modal Logic S5-Satisfiability Problem Thirty-First AAAI Conference on Artificial Intelligence, Feb 2017, San Francisco, United States*

# Requirements

- Python **>3.0**
- Lark library for python
- z3 for python

Install them with :
```
pip install lark 
```
and
```
pip install z3-solver
```

# Usage

## SAT for S5
From the command line:

```
python s5_solver.py
```

and you will see all the options for the sat solver. A simple example:

```
python s5_solver.py -i "E E x"
```
This will check whether the S5 formula "E(E(X))" is SAT

## SAT for Kh

The command line:
```
python kh_solver.py
```
executes the solver for Kh formulas, it takes a plain Kh formulas without nested modalities of the style:
```
kh(p,q);kh(s,t);~kh(p,t)
```
and checks whether the given collection of knowing hows is sat or not.


# Syntax

The syntax for a S5 formula is:

- "&" : Boolean and
- "|" : Boolean or
- "~" : Boolean not
- "A" : box modality
- "E" : diamond modality
 
for Knowing-how formulas you have the knowing how modality, without nested modalities, i.e.:
```
kh(A,B)
```
where `A` and `B` are Boolean formulas without modalities. 



# Author

Pablo F. Castro (pablofcastro@gmail.com)

