
"""
This module provide the basic behavior for performing SAT solving over plain Kh
the input of the solver is a sequence of negated or basic modal formulas, for instance:
kh(p,q);kh(s,t);~kh(x,y)
"""
import argparse, os
import Kh.parser_kh as khparser
import Kh.AST_kh as astkh
import s5_solver as s5solver
from z3 import *
import sys
import time
import itertools
from functools import reduce # foldl
sys.setrecursionlimit(5000)

verbose = False # the tools shows more information hwne verbose is true
start_time = 0 # to save the start_time for the sat
end_time = 0 # to save the end time

def validate_file(f):
    """
        Auxiliar function to check if a file exists
    """
    if not os.path.exists(f):
        # error: argument input: x does not exist
        raise argparse.ArgumentTypeError(f"Couldn't find {f}.")
    return f

def Pi(D, I) :
    """
    This implements the set of indexes \\Pi(D) as described in the paper
    """
    result = {(i,i) for i in I}
    for i in I :
        new_pairs = {(s,t) for (s,u) in result for t in I if (u,t) not in D} 
        result = result.union(new_pairs)
    return result

def translate_s5(problem) :
    """ 
    This method translate a kh formula to a s5 and perform a sat solving over it
    """
    assert isinstance(problem, astkh.Clauses)
    start_time = time.perf_counter()
    # we clasify the clauses into positive and negative
    pos_forms = [form for form in problem.clauses if isinstance(form, astkh.Kh)]
    neg_forms = [form for form in problem.clauses if isinstance(form, astkh.NKh)]
    I = range(1,len(pos_forms)+1) # number of positive forms
    J = range(1,len(neg_forms)+1) # number of negative forms
    IxI =  itertools.product(I, I)
    for n in range(1,len(pos_forms)*len(pos_forms)+1) :
        for D in itertools.combinations(list(IxI), n) :
            elems = set(D)
            Pi_D = Pi(D,I)
            # we construct the S5 forms
            # the first conjunct
            first_and = astkh.Top()
            # the following cycle compute: \bigwedge_{i \in I} E(\psi_j \wedge \neg \xi_i)
            for f in pos_forms :
                first_and = astkh.And(first_and, astkh.Or(astkh.Box(astkh.Not(f.left)), astkh.Diamond(f.right)))
            second_and = astkh.Top()
            # now we compute the big conjunction:  
            for f in neg_forms :
                # E(\psi_j \wedge \neg \xi_j)
                second_and = astkh.And(second_and, astkh.Diamond(astkh.And(f.left, astkh.Not(f.right))))
                third_and = astkh.Top()
                # we calculate: \Bigwedge_{(t,s) \in D} E(\xi_t \wedge \neg \psi_s)
                for t,s in D :
                    third_and = astkh.And(third_and, astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(pos_forms[s-1].left))))
                second_and = astkh.And(second_and, third_and)

                # now we calculate the last And
                fourth_and = astkh.Top()
                for s,t in Pi_D :
                    or_form = astkh.Or(astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right))))
                    fourth_and = astkh.And(fourth_and, or_form)
                second_and = astkh.And(second_and, fourth_and) 
            final_form = astkh.And(first_and, second_and) # this is the final form
            if (verbose) :
                print("Formula checked: "+str(final_form))
                print("D: "+str(D))
                print("Pi(D): "+str(Pi_D))
            z3_model = s5solver.get_model(final_form)
            result = z3_model.check()
            if result == sat :
                end_time = time.perf_counter()
                print("The formula is SAT.")
                if (verbose) :
                    print("Model:")
                    print(z3_model.model())
                print(f"Time: {str(end_time - start_time)} seconds." )
                return
    # if there is no positive forms we have to check only the negative ones
    if (pos_forms == []) :
        second_and = astkh.Top()
        # now we compute the big conjunction:  
        for f in neg_forms :
            # E(\psi_j \wedge \neg \xi_j)
            second_and = astkh.And(second_and, astkh.Diamond(astkh.And(f.left, astkh.Not(f.right))))
        if verbose :
            print(second_and)
        z3_model = s5solver.get_model(second_and)
        result = z3_model.check()
        if result == sat :
            end_time = time.perf_counter()
            print("The formula is SAT.")
            if verbose :
                print("Model:")
                print(z3_model.model())
            print(f"Time: {str(end_time - start_time)} seconds." )
            return # we exit because a solution was found
    end_time = time.perf_counter()
    print("the formula is unsat")
    print(f"Time: {str(end_time - start_time)} seconds." )


def translate_s5_optimized(problem) :
    """ 
    This method translate a kh formula to a s5 and perform a sat solving over it
    """
    assert isinstance(problem, astkh.Clauses)
    start_time = time.perf_counter()
    # we clasify the clauses into positive and negative
    pos_forms = [form for form in problem.clauses if isinstance(form, astkh.Kh)]
    neg_forms = [form for form in problem.clauses if isinstance(form, astkh.NKh)]
    I = range(1,len(pos_forms)+1) # number of positive forms
    J = range(1,len(neg_forms)+1) # number of negative forms
    IxI =  itertools.product(I, I)
    first_and = astkh.Top()
    # the following cycle compute: \bigwedge_{i \in I} E(\psi_j \wedge \neg \xi_i)
    for f in pos_forms :
        first_and = astkh.And(first_and, astkh.Or(astkh.Box(astkh.Not(f.left)), astkh.Diamond(f.right)))
    second_and = astkh.Top()
    for f in neg_forms :
        second_and = astkh.And(second_and, astkh.Diamond(astkh.And(f.left, astkh.Not(f.right))))
    for n in range(1,len(pos_forms)*len(pos_forms)+1) :
        for D in itertools.combinations(list(IxI), n) :
            elems = set(D)
            Pi_D = Pi(D,I)
            # we construct the S5 forms        
            #second_and = astkh.Top()
            # now we compute the big conjunction:  
            third_and = astkh.Top()
            fourth_and = astkh.Top()
            for f in neg_forms :
                # E(\psi_j \wedge \neg \xi_j)
                #second_and = astkh.And(second_and, astkh.Diamond(astkh.And(f.left, astkh.Not(f.right))))
                third_and = astkh.Top()
                # we calculate: \Bigwedge_{(t,s) \in D} E(\xi_t \wedge \neg \psi_s)
                for t,s in D :
                    third_and = astkh.And(third_and, astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(pos_forms[s-1].left))))
                #second_and = astkh.And(second_and, third_and)

                # now we calculate the last And
                fourth_and = astkh.Top()
                for s,t in Pi_D :
                    or_form = astkh.Or(astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right))))
                    fourth_and = astkh.And(fourth_and, or_form)
                #second_and = astkh.And(second_and, fourth_and) 
            final_form = astkh.And(first_and, second_and) # this is the final form
            final_form = astkh.And(final_form, third_and)
            final_form = astkh.And(final_form, fourth_and)
            if (verbose) :
                print("Formula checked: "+str(final_form))
                print("D: "+str(D))
                print("TC(~D): "+str(Pi_D))
            z3_model = s5solver.get_model(final_form)
            result = z3_model.check()
            if result == sat :
                end_time = time.perf_counter()
                print("The formula is SAT.")
                if (verbose) :
                    print("Model:")
                    print(z3_model.model())
                print(f"Time: {str(end_time - start_time)} seconds." )
                return
    # if there is no positive forms we have to check only the negative ones
    if (pos_forms == []) :
        second_and = astkh.Top()
        # now we compute the big conjunction:  
        for f in neg_forms :
            # E(\psi_j \wedge \neg \xi_j)
            second_and = astkh.And(second_and, astkh.Diamond(astkh.And(f.left, astkh.Not(f.right))))
        if verbose :
            print(second_and)
        z3_model = s5solver.get_model(second_and)
        result = z3_model.check()
        if result == sat :
            end_time = time.perf_counter()
            print("The formula is SAT.")
            if verbose :
                print("Model:")
                print(z3_model.model())
            print(f"Time: {str(end_time - start_time)} seconds." )
            return # we exit because a solution was found
    end_time = time.perf_counter()
    print("The formula is UNSAT")
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
        parsed_form = khparser.parse(problem)
        translate_s5_optimized(parsed_form)
    elif args.file :
        file_name = args.file 
        with open(file_name, "r") as file:
            problem = file.read()
            #print(problem)
            parsed_form = khparser.parse(problem)
            #translate_s5(parsed_form)
            translate_s5_optimized(parsed_form)
    else :
        parser.print_help(sys.stderr)
        sys.exit(1)