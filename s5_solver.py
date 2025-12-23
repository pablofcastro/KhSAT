import argparse, os
import S5.toSAT as tosat
import S5.NNFVisitor as tonnf
import S5.DiamondVisitor as diamond_counter
import S5.parser_s5 as s5parser
from z3 import *
import sys
import time

verbose = False

def validate_file(f):
    if not os.path.exists(f):
        # error: argument input: x does not exist
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

def satS5(formula) :
    start_time = time.perf_counter()
    # a nnf visitor is created
    nnf_visitor = tonnf.ToNNF()
    # a diamond visitor is created
    diamond_visitor = diamond_counter.DiamondVisitor()
    # formula is parser
    parsed_form = s5parser.parse(formula)
    # the formula is translated to nnf
    nnf_form = parsed_form.accept(nnf_visitor)
    # we count the number of diamonds
    n = nnf_form.accept(diamond_visitor)
    # we translate the formula to sat
    sat_visitor = tosat.ToSAT(n+1)
    boolean_form = nnf_form.accept(sat_visitor,1)
    if (verbose) :
        print("Parsed Formula:"+str(parsed_form))
        print("NNF Formula: "+str(nnf_form))
        print("Diamond Depth: "+str(n+1))
        print("Boolean Formula: "+str(boolean_form))

    s = Solver()
    s.add(boolean_form)
    result = s.check()
    end_time = time.perf_counter()
    if result == sat :
        print("The formula is SAT.")
        print("Model:")
        print(s.model())
    else :
        print("the formula is unsat")
    print(f"Time: {str(end_time - start_time)} seconds." )

if __name__ == "__main__" :
    """ This is the main function of the solver 
        the options can be:
        + --help: shows the options
        + --file (-f): process a file
        + --inline (-i): takes a formula from the command line
        + --verbose (-v): increase the output verbosity
    """
    parser = argparse.ArgumentParser()
    file = ""
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-f", "--file", dest="file", type=validate_file,
                        help="the file with the formula", metavar="FILE")
    parser.add_argument("-i", "--inline", dest="form", help="takes a formula as inline input", metavar="FORMULA")
    args = parser.parse_args()
    
    if args.verbose :
        verbose = True 
    if args.form :
        problem = args.form
        satS5(problem)
    elif args.file :
        file_name = args.file 
        with open(file_name, "r") as file:
            problem = file.read() 
            satS5(problem)
    else :
        parser.print_help(sys.stderr)
        sys.exit(1)



