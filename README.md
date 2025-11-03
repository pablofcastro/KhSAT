# Project Name

A SAT solver for the logics S5 and Kh

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

From the command line:

```
python s5_solver.py
```

and you will see all the options for the sat solver. A simple example:

```
python s5_solver.py -i "E E x"
```
This will chec whether the S5 formula "E(E(X))" is SAT

# Syntax

The syntax for the formula is:

- "&" : boolean and
- "|" : boolean or
- "~" : boolean not
- "A" : box modality
- "E" : diamond modality
 

