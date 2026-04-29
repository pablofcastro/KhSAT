
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

def translate_s5_optimized_bis(problem) :
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
            # 
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

    # there are positive and negative atoms
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

    I = range(1,len(pos_forms)+1) # number of positive forms
    IxI =  itertools.product(I, I)
    #first_and = astkh.Top()
    l = list(IxI) # the list corresponding to the IxI
    for n in range(0,len(pos_forms)*len(pos_forms)+1) :
        for D in itertools.combinations(l, n) :
            elems = set(D)
            Pi_D = Pi(D,I)
            # we construct the S5 forms        
            # now we compute the big conjunction:  
            third_and = astkh.Top()
            fourth_and = astkh.Top()

            for f in neg_forms :
                for s,t in Pi_D :
                    or_form = astkh.Or(astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right))))
                    third_and = astkh.And(third_and, or_form)
                #second_and = astkh.And(second_and, fourth_and)

            for t,s in D :
                fourth_and = astkh.And(fourth_and, astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(pos_forms[s-1].left)))) 

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
            # 
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

    # there are positive and negative atoms
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

    I = range(1,len(pos_forms)+1) # number of positive forms
    # Iteramos sobre itertools.product y lo guardamos directamente en la lista l
    l = list(itertools.product(I, I)) 

    # For each j, s, t, save the satisfiability of the formula: Θ+ ∧ Θ- ∧ (E(ψj ∧ ¬ψs) ∨ E(χt ∧ ¬χj))
    green_results = {}
    
    print(f"Número de positivos (|I|): {len(I)}, Lista |IxI|: {len(l)}")
    print("Iniciando pre-cálculo de la diagonal (s=t) para green_results...")
    
    # Primero iteramos los valores donde s == t
    for j, f in enumerate(neg_forms):
        for s in I:
            t = s
            print(f"  -> green_results_diagonal: Evaluando j={j}, s=t={s}")
            or_form = astkh.Or(
                astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), 
                astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right)))
            )
            form_to_check = astkh.And(astkh.And(first_and, second_and), or_form)
            z3_model_or = s5solver.get_model(form_to_check)
            
            if z3_model_or.check() != sat:
                print("UNSAT")
                print(f"Pruned directly from preprocessing because it was UNSAT for j={j} and s=t={s}")
                end_time = time.perf_counter()
                print(f"Time: {str(end_time - start_time)} seconds." )
                return
                
            green_results[(j, s, t)] = True

    print("Diagonal evaluada. Iniciando pre-cálculo para s != t en green_results...")
    # Despues iteramos sobre el resto donde s != t
    for j, f in enumerate(neg_forms):
        for s, t in l:
            if s == t:
                continue
                
            print(f"  -> green_results_rest: Evaluando j={j}, s={s}, t={t}")
            or_form = astkh.Or(
                astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), 
                astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right)))
            )
            
            # Check if it is SAT in conjunction with Θ+ and Θ-
            form_to_check = astkh.And(astkh.And(first_and, second_and), or_form)
            z3_model_or = s5solver.get_model(form_to_check)
            is_sat = (z3_model_or.check() == sat)
            
            # Save results using the tuple (j, s, t) as key
            green_results[(j, s, t)] = is_sat

    print("green_results finalizado. Iniciando pre-cálculo de red_results...")
    print("=== green_results ===")
    for k, v in green_results.items():
        print(f"  {k}: {v}")
    print("=====================")
    # For each s, t in IxI save the satisfiability of the formula: Θ+ ∧ Θ- ∧ E(χt ∧ ¬ψs)
    red_results = {}
    for t, s in l:
        print(f"  -> red_results: Evaluando t={t}, s={s}")
        diamond_form = astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(pos_forms[s-1].left)))
        
        # Check if it is SAT in conjunction with Θ+ and Θ-
        form_to_check = astkh.And(astkh.And(first_and, second_and), diamond_form)
        z3_model_diamond = s5solver.get_model(form_to_check)
        is_sat = (z3_model_diamond.check() == sat)
        
        # Save results using the tuple (t, s) as key
        red_results[(t, s)] = is_sat

    print("red_results finalizado. Comenzando la evaluación de las combinaciones (D)...")
    print("=== red_results ===")
    for k, v in red_results.items():
        print(f"  {k}: {v}")
    print("===================")
    solver_calls_loop = 0
    for n in range(0,len(pos_forms)*len(pos_forms)+1) :
        print(f"==> Evaluando subconjuntos de tamaño n={n}")
        for D in itertools.combinations(l, n) : #demasiado
            Pi_D = Pi(D,I)
            
            # If any green_results is False for any j and (s, t) in Pi_D, skip to the next D.
            if any(not green_results[(j, s, t)] for j in range(len(neg_forms)) for s, t in Pi_D):
                continue
            # If any red_results is False for any (t, s) in D, skip to the next D.
            if any(not red_results[(t, s)] for t, s in D):
                continue

            # we construct the S5 forms        
            # now we compute the big conjunction:  
            third_and = astkh.Top()
            fourth_and = astkh.Top()

            for f in neg_forms :
                for s,t in Pi_D :
                    or_form = astkh.Or(astkh.Diamond(astkh.And(f.left, astkh.Not(pos_forms[s-1].left))), astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(f.right))))
                    third_and = astkh.And(third_and, or_form)
                #second_and = astkh.And(second_and, fourth_and)

            for t,s in D :
                fourth_and = astkh.And(fourth_and, astkh.Diamond(astkh.And(pos_forms[t-1].right, astkh.Not(pos_forms[s-1].left)))) 

            final_form = astkh.And(first_and, second_and) # this is the final form
            final_form = astkh.And(final_form, third_and)
            final_form = astkh.And(final_form, fourth_and)
            if (verbose) :
                print("Formula checked: "+str(final_form))
                print("D: "+str(D))
                print("TC(~D): "+str(Pi_D))
            z3_model = s5solver.get_model(final_form)
            result = z3_model.check()
            solver_calls_loop += 1
            print(f"Llamadas iterativas al solver: {solver_calls_loop}")
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