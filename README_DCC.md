# S5 Solver with DCC

A SAT solver for S5 with DCC (Diamond Conflict Coloring) and IWB (Incremental World Bound).

## Requirements

- `Python >3.0`
- `Lark library for python`
- `z3 library for python`

Install them with :
```bash
pip install lark 
```

and
```bash
pip install z3-solver
```

> Note: In some system you have to use the command `python3` and `pip3` instead of `python` and `pip`.

## Ubuntu
In UBUNTU and other Linux distributions you can also install them using `apt-get`, for instance:

For installing Lark:
```bash
sudo apt install python3-lark
```


For installing Z3:
```bash
sudo apt install python3-z3
```


## Formula syntax

The solver accepts formulas in two formats.

### S5 format

This is the default format; do not pass `--intohylo`.

- `E` means diamond and `A` means box: `E x`, `A x`.
- `~` means negation, `&` conjunction, and `|` disjunction.
- Parentheses can be used to group expressions. The constants `true` and `false` are also supported.
- `&` has higher precedence than `|`. For example, `x | y & z` is interpreted as `x | (y & z)`.
- Variable names start with a lowercase letter or `_`, followed by lowercase letters, digits, or `_`.

Examples:

```text
E x
A (x | ~y)
E E x
```

### IntoHylo format

Pass `--intohylo` to use this format. Formulas must be enclosed by `begin` and `end`.

- `<r1>` means diamond and `[r1]` means box.
- `~`, `&`, `|`, parentheses, `true`, and `false` are supported.
- Implication (`->`) and equivalence (`<->`) are also supported.
- Variables must be `p` followed by one or more digits, such as `p1` or `p23`.
- Relation labels must be `r` followed by one or more digits, such as `r1`.
- `|` has higher precedence than `&` in this format. Use parentheses to make the intended grouping clear.

Examples:

```text
begin <r1> p1 end
begin [r1] (p1 | ~p2) end
begin p1 -> <r1> p2 end
```

## Usage

First you have to go to the main folder. For example, if the main folder is KhSAT:

```bash
cd KhSAT
```


Now, from the command line you can execute:

```bash
python s5_solver_dcc.py
```


and you will see all the options for the solver. A simple example:

```bash
python s5_solver_dcc.py -i "E E x"
```

It can also be executed using the following command with the intohylo format:
```bash
python s5_solver_dcc.py --intohylo -i "begin <r1> <r1> p1 end"
```


This will check whether the S5 formula "E(E(X))" is SAT.

The solver also accepts files as inputs with the option -f. For example:

```bash
python s5_solver_dcc.py -f Examples/formula1.s5
```

Other variant is:
```bash
python s5_solver_dcc.py --intohylo -f Examples/formula1.intohylo
```

### Options

- `-i`, `--inline` - takes a formula as inline input
- `-f`, `--file` - the file with the formula
- `-v`, `--verbose` - increase output verbosity
- `--intohylo` - interprets diamonds as `<r1>` and boxes as `[r1]`

## Benchmarks

### Run the test suite

```bash
python test.py
```
`test.py` runs the deterministic test suite of the solver. It pushes 22 edge cases -
propositional basics, violations of the S5 axioms K, T, 4 and 5, modal dualities,
box/diamond conflicts and nested modal depth - through the internal pipeline
(NNF -> modal collapse -> DCC world bound -> SAT translation -> Z3) and checks that each
one returns the expected SAT/UNSAT verdict, re-verifying every SAT model with the Kripke
`S5ModelChecker`. Three extra cases check the robustness of the model checker itself
(invalid root world, orphan world in the valuation, corrupted model). The suite finishes
with a summary of the passed tests.

> Note: the formulas are built directly in the AST, so this script does not exercise the
parser.

### Run DCC fuzzing tests


```bash
python test_fuzzing_dcc.py
```
`test_fuzzing_dcc.py` stresses the DCC chromatic bound with incompatible-diamond cliques
(K3 and K4, requiring at least 3 and 4 worlds) and then fuzzes 50 random S5 formulas,
verifying that every SAT model is accepted by the `S5ModelChecker`.

### Compare against Cheetah

You can compare the solver against the S5 Cheetah2.0 solver.

Prerequisites (not included in the repository):

- The `Cheetah2.0` executable, located anywhere and passed with `--cheetah-bin` (default: `./Cheetah2.0`).
- A folder with benchmark formulas (`.s5` or `.intohylo` files), passed with `--folder` (default: `formulasCheetahS5` in the project root).

The benchmark formulas are available in [this Google Drive folder](https://drive.google.com/drive/folders/1amtcF3VoWUthrBfqWBzj9XyBsLnJN28i). The archive is too large to include in the repository; download it from the link, extract it, and pass the folder containing the formulas with `--folder`.

The solver also accepts formulas in the default S5 format, but the comparison script runs KhSAT using IntoHylo syntax. All formulas in the Google Drive folder are in IntoHylo format

Run from the main folder (`KhSAT`):

```bash
python Benchmark/scriptsS5/cheetah_benchmarks.py --runs 5 --timeout 300
```

Each formula is solved by both solvers `--runs` times and the median time is reported. The results are saved in `tiempos_comparacion/cheetah_vs_khsat.csv` with the verdicts (SAT/UNSAT), generated Kripke worlds, solver times, the speedup `total_time_cheetah / total_time_khsat` and the Kripke model verification for KhSAT. A summary with the soundness match, verified models and win counts for each solver is printed at the end.

#### Options

- `--folder` - folder with the benchmark formulas (default: `formulasCheetahS5`)
- `--cheetah-bin` - path to the Cheetah2.0 executable (default: `./Cheetah2.0`)
- `--solver-script` - path to the KhSAT solver (default: `s5_solver_dcc.py`)
- `--runs` - executions per formula for the median time (default: `1`)
- `--timeout` - timeout in seconds per solver run (default: `300`)

> Note: absolute paths are used as given; relative paths for `--folder`, `--cheetah-bin` and `--solver-script` are resolved from the project root, not from the current directory. The output CSV is written relative to the directory where you run the script.

Previous comparison results can be found in the `tiempos_comparacion/` folder.