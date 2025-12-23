# Project Name

A SAT solver for the logics S5 and the Knowing-How logic KH.

The algorithm for S5 is based on the paper:

*Thomas Caridroit, Jean-Marie Lagniez, Daniel Le Berre, Tiago de Lima, Valentin Montmirail.  A SAT Based Approach for Solving the Modal Logic S5-Satisfiability Problem Thirty-First AAAI Conference on Artificial Intelligence, Feb 2017, San Francisco, United States*

The Knowing-how logic is the one presented at:

*Y. Wang. A logic of knowing how. In 5th International Workshop on Logic, Rationality, and Interaction (LORI 2015), volume 9394 of Lecture Notes in Computer Science, pages 392–405. Springer, 2015.*

# Requirements

- Python **>3.0**
- Lark library for python
- z3 library for python

Install them with :
```
pip install lark 
```
and
```
pip install z3-solver
```

In UBUNTU and other Linux distributions you can also install them using apt-get.

# Usage

## SAT for S5

First you have to go to the main folder. For example, if the main folder is `KhSAT`:
```
cd KhSAT
```
Now, from the command line you can execute:

```
python s5_solver.py
```

and you will see all the options for the SAT solver. A simple example:

```
python s5_solver.py -i "E E x"
```

This will check whether the S5 formula "E(E(X))" is SAT.

THh S5 SAT solver also accepts files as inputs with the option -f. For example:

```
python s5_solver.py -f Examples/formula1.s5
```

## SAT for Kh

The command line:
```
python kh_solver.py
```
executes the solver for Kh formulas, it takes a plain Kh formulas without nested modalities of the style:
```
Kh(p,q);Kh(s,t);~Kh(p,t)
```
and checks whether the given collection of knowing hows is sat or not.

The command takes a formula from the command line (with the -i option) or from a file. For example:
```
python kh_solver -i 'Kh(p,q);Kh(s,t);~Kh(p,t)'
```
checks the satisfiability of the given formula.

For checking the satisfiability of a formula in a file you have to use the option -f. For example:

```
python kh_solver -i Examples/formula1.kh
```

The option -v activates the verbose mode, the tool will display useful information about the result obtained (SAT or UNSAT).

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

# Benchmark

A benchmark is provided with the tool in the folder `Benchmark` as well as several scripts for  running the benchmark.

The benchmark consists of 500 randomly generated formulas as follows. For each 1 ≤ k ≤ 50, we generated 10 formulas with p positive occurrences of the Kh modality and q occurrences of ~Kh, where p is chosen uniformly at random from the interval [0, k]. Similarly, q is chosen uniformly at random from the interval [0, k−p]. 

The folder `Benchmark/scripts` contains scripts for generating and running the benchmark.

Typically you don't need to generate the benchamrk again. In the case you want to do it, the script `Benchmark/scripts/main.py` can be used for generating the benchmark. 

**If you generate the benchmark the generated files will be different from the ones in the repository since they are ramdomly generated**

## Running the Benchmark

For running the batch you can use the script `Benchmark/scripts/run_benchmark.py` (from the main folder), you can run the benchmark by batches with the option --benchmark. For instance:

```
cd Benchmark/scripts/
python run_benchmark --benchmark 1
```
runs the first batch of the examples consisting of formulas with k <= 10, as explained above. Similarly, you can run the script with 1,2,3,4,5.
The results of the benchmark are saved in files .csv in files corresponding to the argument, for instance, in the example above you will get a 
file output-batch1.csv

## Generating the graphic

If you want to generate a plot from the results wout can use the script `generate_plot.py`.

```
cd Benchmark/scripts/
python generate_plot.py
```

this generates the plot. 

# License

SATKh is distributed under GPL V3.0 License.

