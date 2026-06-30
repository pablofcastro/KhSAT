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
sys.setrecursionlimit(1000000)

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
    z3_model = s5solver.get_model(astkh.And(first_and, second_and))
    result = z3_model.check()
    if result != sat :
        print("UNSAT")
        #print("Formula: theta /\ theta' is unsat")
        print("Rest of formulas unprocesed.")
        end_time = time.perf_counter()
        print(f"Time: {str(end_time - start_time)} seconds." )
        return 
    i = 0
    l = list(IxI) # the list corresponding to the IxI
    for n in range(0,len(pos_forms)*len(pos_forms)+1) :
        for D in itertools.combinations(l, n) :
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
                #fourth_and = astkh.Top()
                for s,t in Pi_D :
                    or_form = astkh.Or(astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right))))
                    fourth_and = astkh.And(fourth_and, or_form)
                #second_and = astkh.And(second_and, fourth_and) 
            final_form = astkh.And(first_and, second_and) # this is the final form
            final_form = astkh.And(final_form, third_and)
            final_form = astkh.And(final_form, fourth_and)

            print(type(final_form))
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

def translate_s5_optimized_lu(problem) :
    """ 
    This method translate a kh formula to a s5 and perform a sat solving over it
    """
    assert isinstance(problem, astkh.Clauses)
    start_time = time.perf_counter()

    # we clasify the clauses into positive and negative
    pos_forms = [form for form in problem.clauses if isinstance(form, astkh.Kh)]
    neg_forms = [form for form in problem.clauses if isinstance(form, astkh.NKh)]

    # if there is no negative forms we have to check only the positive ones
    if (neg_forms == []) :
        first_and = astkh.Top()
        # now we compute the big conjunction:  
        for f in pos_forms :
            # Θ+
            first_and = astkh.And(first_and, astkh.Or(astkh.Box(astkh.Not(f.left)), astkh.Diamond(f.right)))
        if verbose :
            print(first_and)
        z3_model = s5solver.get_model(first_and)
        result = z3_model.check()
        if result == sat :
            end_time = time.perf_counter()
            print("The formula is SAT.")
            if verbose :
                print("Model:")
                print(z3_model.model())
            print(f"Time: {str(end_time - start_time)} seconds." )
            return # we exit because a solution was found

    # if there is no positive forms we have to check only the negative ones
    if (pos_forms == []) :
        second_and = astkh.Top()
        # now we compute the big conjunction:  
        for f in neg_forms :
            # Θ-
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

    # there are positive and negative atoms
    # First, check SAT for Θ+ ∧ Θ- 
    first_and = astkh.Top()
    for f in pos_forms :
        first_and = astkh.And(first_and, astkh.Or(astkh.Box(astkh.Not(f.left)), astkh.Diamond(f.right)))
    second_and = astkh.Top()
    for f in neg_forms :
        second_and = astkh.And(second_and, astkh.Diamond(astkh.And(f.left, astkh.Not(f.right))))
    z3_model = s5solver.get_model(astkh.And(first_and, second_and))
    result = z3_model.check()
    if result != sat :
        print("UNSAT")
        print("Formula: theta /\\ theta' is unsat")
        print("Rest of formulas unprocesed.")
        end_time = time.perf_counter()
        print(f"Time: {str(end_time - start_time)} seconds." )
        return 

    # number of positive forms
    I = range(1,len(pos_forms)+1) 
    # Generate the Cartesian product IxI
    IxI = list(itertools.product(I, I)) 

    # For each j, s, t, save the satisfiability of the formula: Θ+ ∧ Θ- ∧ (E(ψj ∧ ¬ψs) ∨ E(χt ∧ ¬χj))
    theta_D_disj_sat = {}
    
    # Set of mandatory pairs that MUST be in D (because they break the disjunction condition)
    theta_D_disj_sat_false = set()
    
    print(f"Number of positives (|I|): {len(I)}, List |IxI| size: {len(IxI)}")
    print("Starting pre-computation for cases where s=t for theta_D_disj_sat...")
    
    # Check cases where (s == t)
    for j, f in enumerate(neg_forms, 1):
        for s in I:
            t = s
            print(f"  -> theta_D_disj_sat: j={j}, s=t={s}")
            or_form = astkh.Or(
                astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), 
                astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right)))
            )

            # Check if it is SAT in conjunction with Θ+ and Θ-
            form_to_check = astkh.And(astkh.And(first_and, second_and), or_form)
            z3_model_or = s5solver.get_model(form_to_check)
            
            # Check SAT; if it fails, the entire formula is UNSAT because the identity is always required
            if z3_model_or.check() != sat:
                print("UNSAT")
                print(f"Pruned directly from preprocessing because it was UNSAT for j={j} and s=t={s}")
                end_time = time.perf_counter()
                print(f"Time: {str(end_time - start_time)} seconds." )
                return

            # Save results using the tuple (j-1, s-1, t-1) as key    
            theta_D_disj_sat[(j-1, s-1, t-1)] = True

    print("s=t evaluation complete. Starting pre-computation for s != t in theta_D_disj_sat...")
    # Iterate over the rest of the entries where (s != t)
    for j, f in enumerate(neg_forms, 1):
        for s, t in IxI:
            if s == t:
                continue
                
            print(f"  -> theta_D_disj_sat: j={j}, s={s}, t={t}")
            or_form = astkh.Or(
                astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), 
                astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right)))
            )
            
            # Check if it is SAT in conjunction with Θ+ and Θ-
            form_to_check = astkh.And(astkh.And(first_and, second_and), or_form)
            z3_model_or = s5solver.get_model(form_to_check)
            is_sat = (z3_model_or.check() == sat)
            
            # Save results using the tuple (j-1, s-1, t-1) as key
            theta_D_disj_sat[(j-1, s-1, t-1)] = is_sat
            if not is_sat:
                # If it's UNSAT, the edge (s, t) cannot be in the transitive closure Pi(D).
                # Therefore, we MUST include (s, t) in D to avoid unsat.
                theta_D_disj_sat_false.add((s, t))

    
    print("=== theta_D_disj_sat ===")
    for k, v in theta_D_disj_sat.items():
        print(f"  {k}: {v}")
    print("=====================")

    print("green_results finalizado. Iniciando pre-cálculo de red_results...")

    # For each t, s in IxI save the satisfiability of the formula: Θ+ ∧ Θ- ∧ E(χt ∧ ¬ψs)
    theta_D_exist_sat = {}
    
    # Set of forbidden pairs that CANNOT be in D (because they break the conjunction condition)
    theta_D_exist_sat_false = set()
    for t, s in IxI:
        print(f"  -> red_results: t={t}, s={s}")
        diamond_form = astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(pos_forms[s-1].left)))
        
        # Check if it is SAT in conjunction with Θ+ and Θ-
        form_to_check = astkh.And(astkh.And(first_and, second_and), diamond_form)
        z3_model_diamond = s5solver.get_model(form_to_check)
        is_sat = (z3_model_diamond.check() == sat)
        
        # Save results using the tuple (t-1, s-1) as key
        theta_D_exist_sat[(t-1, s-1)] = is_sat
        if not is_sat:
            # If it's UNSAT, this specific edge (t, s) is strictly forbidden from being in D.
            theta_D_exist_sat_false.add((t, s))

    print("=== theta_D_exist_sat ===")
    for k, v in theta_D_exist_sat.items():
        print(f"  {k}: {v}")
    print("===================")

    solver_calls_loop = 0



    print(f"theta_D_disj_sat_false: {theta_D_disj_sat_false}")
    print(f"theta_D_exist_sat_false: {theta_D_exist_sat_false}")

    # Check for contradictions: If a pair must be in D but is also forbidden from D,
    # then no valid subset D can exist, and the formula is UNSAT.
    intersection = theta_D_disj_sat_false.intersection(theta_D_exist_sat_false)
    if intersection:
        print("Intersection between theta_D_disj_sat_false and theta_D_exist_sat_false is not empty!")
        print(f"Intersection: {intersection}")
        end_time = time.perf_counter()
        print("The formula is UNSAT")
        print(f"Time: {str(end_time - start_time)} seconds." )
        return

    # The search space for D is IxI minus the forbidden pairs and the mandatory pairs.
    IxI_filtered = set(IxI) - theta_D_exist_sat_false - theta_D_disj_sat_false

    # Iterate over all valid subsets D_subset of IxI_filtered
    print("theta_D_exist_sat complete. Starting evaluation of combinations (D)...")
    for n in range(len(IxI_filtered), -1, -1) :
        print(f"==> Evaluating subsets of size n={n} (total D size: {n + len(theta_D_disj_sat_false)})")
        for D_subset in itertools.combinations(IxI_filtered, n) : 
            # D is constructed by taking a valid subset and enforcing the mandatory pairs
            D = set(D_subset).union(theta_D_disj_sat_false)
            Pi_D = Pi(D,I)
            
            # If any theta_D_disj_sat is False for any j and (s, t) in Pi_D, skip to the next D.
            if any(not theta_D_disj_sat[(j, s-1, t-1)] for j in range(len(neg_forms)) for s, t in Pi_D):
                continue

            # Not necessary
            # If any theta_D_exist_sat is False for any (t, s) in D, skip to the next D.
            #if any(not theta_D_exist_sat[(t-1, s-1)] for t, s in D):
            #    continue

            # we construct the S5 forms        
            # now we compute the big conjunction:  
            third_and = astkh.Top()
            fourth_and = astkh.Top()

            for f in neg_forms :
                for s,t in Pi_D :
                    or_form = astkh.Or(astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right))))
                    third_and = astkh.And(third_and, or_form)

            for t,s in D :
                fourth_and = astkh.And(fourth_and, astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(pos_forms[s-1].left)))) 

            final_form = astkh.And(first_and, second_and) 
            final_form = astkh.And(final_form, third_and)
            final_form = astkh.And(final_form, fourth_and)
            if (verbose) :
                print("Formula checked: "+str(final_form))
                print("D: "+str(D))
                print("TC(~D): "+str(Pi_D))
            z3_model = s5solver.get_model(final_form)
            result = z3_model.check()

            solver_calls_loop += 1
            print(f"Solver calls: {solver_calls_loop}")

            if result == sat :
                end_time = time.perf_counter()
                print("The formula is SAT.")
                if (verbose) :
                    print("Model:")
                    print(z3_model.model())
                print(f"Time: {str(end_time - start_time)} seconds." )
                return

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
    parser.add_argument("-m", "--method", dest="method", choices=["new", "old"], default="new", help="choose the translation method")
    args = parser.parse_args()
    
    if args.verbose :
        verbose = True 
    if args.form :
        problem = args.form
        parsed_form = khparser.parse(problem)
        if args.method == "new":
            translate_s5_optimized_lu(parsed_form)
        else:
            translate_s5_optimized(parsed_form)
    elif args.file :
        file_name = args.file 
        with open(file_name, "r") as file:
            problem = file.read()
            parsed_form = khparser.parse(problem)
            if args.method == "new":
                translate_s5_optimized_lu(parsed_form)
            else:
                translate_s5_optimized(parsed_form)
    else :
        parser.print_help(sys.stderr)
        sys.exit(1)