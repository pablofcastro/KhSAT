import argparse, os
import S5.toSAT as tosat
import S5.NNFVisitor as tonnf
import S5.DiamondVisitor as diamond_counter
import S5.parser_s5 as s5parser
from z3 import *
import sys
import time

sys.setrecursionlimit(10000)

verbose = False

def validate_file(f):
    if not os.path.exists(f):
        raise argparse.ArgumentTypeError(f"Couldn't find {f}.")
    return f

def get_model(parsed_form) : 
    """ It returns a model for performing sat for already constructed formula"""
    nnf_visitor = tonnf.ToNNF()
    # a diamond visitor is created
    diamond_visitor = diamond_counter.DiamondVisitor()
    # formula is parser
    #parsed_form = s5parser.parse(formula)
    # the formula is translated to nnf
    nnf_form = parsed_form.accept(nnf_visitor)
    # we count the number of diamonds
    n = nnf_form.accept(diamond_visitor)
    # we translate the formula to sat
    sat_visitor = tosat.ToSAT(n+1)
    boolean_form = nnf_form.accept(sat_visitor,1)
    s = Solver()
    s.add(boolean_form)
    return s

def satS5(formula, intohylo=False) :
    overall_start = time.perf_counter()
    
    # 1. PARSEO
    t0 = time.perf_counter()
    parsed_form = s5parser.parse(formula, intohylo=intohylo)
    parse_time = time.perf_counter() - t0
    
    # 2. NNF
    t1 = time.perf_counter()
    # a nnf visitor is created
    nnf_visitor = tonnf.ToNNF()
    # a diamond visitor is created
    diamond_visitor = diamond_counter.DiamondVisitor()
    # the formula is translated to nnf
    nnf_form = parsed_form.accept(nnf_visitor)
    nnf_time = time.perf_counter() - t1
    
    # 3. CONTEO DE DIAMANTES Y SAT
    t2 = time.perf_counter()
    diamond_visitor = diamond_counter.DiamondVisitor()
    n = nnf_form.accept(diamond_visitor)
    sat_visitor = tosat.ToSAT(n+1)
    boolean_form = nnf_form.accept(sat_visitor,1)
    to_sat_time = time.perf_counter() - t2
    
    translation_time = time.perf_counter() - overall_start

    if (verbose) :
        print("Parsed Formula:"+str(parsed_form))
        print("NNF Formula: "+str(nnf_form))
        print("Diamond Depth: "+str(n+1))
        print("Boolean Formula: "+str(boolean_form))

    s = Solver()
    s.add(boolean_form)
    
    # -------- Z3 SOLVING --------
    z3_start = time.perf_counter()
    result = s.check()
    z3_time = time.perf_counter() - z3_start
    overall_time = time.perf_counter() - overall_start
    
    if result == sat :
        print("The formula is SAT.")
        if verbose:
            print("Model:")
            print(s.model())
    else :
        print("The formula is unsat.")
        
    # El benchmark leerá exactamente estas líneas
    print(f"Parse time: {parse_time:.6f}")
    print(f"NNF time: {nnf_time:.6f}")
    print(f"To SAT time: {to_sat_time:.6f}")
    print(f"Translation time: {translation_time:.6f}")
    print(f"Z3 time: {z3_time:.6f}")
    print(f"Total time: {overall_time:.6f}")

if __name__ == "__main__" :
    parser = argparse.ArgumentParser()
    file = ""
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-f", "--file", dest="file", type=validate_file,
                        help="the file with the formula", metavar="FILE")
    parser.add_argument("--intohylo", action="store_true", help="interprets diamonds as <r1> and boxes as [r1]")
    parser.add_argument("-i", "--inline", dest="form", help="takes a formula as inline input", metavar="FORMULA")
    args = parser.parse_args()
    
    if args.verbose :
        verbose = True 
    if args.form :
        problem = args.form
        satS5(problem, intohylo=args.intohylo)
    elif args.file :
        file_name = args.file 
        with open(file_name, "r") as file:
            problem = file.read() 
            satS5(problem, intohylo=args.intohylo)
    else :
        parser.print_help(sys.stderr)
        sys.exit(1)