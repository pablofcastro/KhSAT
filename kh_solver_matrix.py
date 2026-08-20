import Kh.AST_kh as astkh
import s5_solver as s5solver
import time
from z3 import *
import argparse, os
import Kh.parser_kh as khparser
from collections import deque

verbose = False

def validate_file(f):
    if not os.path.exists(f):
        raise argparse.ArgumentTypeError(f"Couldn't find {f}.")
    return f

def print_matrix(M_x, M_pre, M_post):
    print("\n=== Matrix M_x ===")
    header = "\t" + "\t".join(str(post) for post in M_post)
    print(header)
    for pre in M_pre:
        row = str(pre) + "\t"
        row += "\t".join("T" if M_x[str(pre)][str(post)] == True else "." for post in M_post)
        print(row)
    print("==================\n")

def print_M(M):
    print("\n=== M (existential pairs) ===")
    for (pre, post) in M:
        print(f"  ({pre}, {post})")
    print("=============================\n")

def print_stack(stack):
    print("\n=== Stack ===")
    for (type, j, g_prev) in stack:
        print(f"  (type={type}, j={j}, G_prev={g_prev})")
    print("=============\n")



def backtracking(G, M, universal_pre, stack, positives):
    """
    Performs backtracking over the positive formulas' decision tree (Kh(A_j, B_j) = Box(~A_j) v Diamond(B_j)).
    
    Unwinds the stack to find the last 'universal' choice, attempts to switch it to 
    'existential', and checks S5-satisfiability with Z3. If valid, updates state (G, M) 
    to resume; otherwise, continues popping or returns UNSAT if exhausted.
    """
    
    while stack:
        type, j, g_prev = stack.pop()
        kh = positives[j]
        pre_j = kh.left
        post_j = kh.right
        pair_j = (pre_j, post_j)

        if (type == "universal"):
            universal_pre.pop()
            g_existential = astkh.And(g_prev, astkh.Diamond(post_j))
            z3_model = s5solver.get_model(g_existential)
            result = z3_model.check()
            if result == sat:
                stack.append(("existential", j, g_prev))
                M.append(pair_j)
                G = g_existential
                if (verbose) :
                    print(f"\n[Backtracking] Found SAT with existential for j={j}, G={G}")
                    print_M(M)
                    print_stack(stack)
                return j, G, M, universal_pre
        else:
            M.pop()

    return "UNSAT", None, None, None

def build_G(positives, pos, G, M, universal_pre, stack):
    """
    Iteratively processes positive formulas from index `pos` to construct the global formula G.

    For each clause Kh(A_i, B_i), it attempts the universal choice Box(~A_i) first.
    If unsatisfiable, it attempts the existential choice Diamond(B_i). If both fail,
    it invokes backtracking to unwind previous choices and find a satisfiable state.
    """

    length_positives = len(positives)
    i = pos

    while (i < length_positives):
        kh = positives[i] #kh(φ_i, ψ_i)
        pre_i = kh.left
        post_i = kh.right
        pair_i = (pre_i, post_i)

        # Attempt universal branch: G ∧ A(~ φ_i)
        g_universal = astkh.And(G, astkh.Box(astkh.Not(pre_i)))
        z3_model = s5solver.get_model(g_universal)
        result = z3_model.check()
        if result == sat:
            stack.append(("universal", i, G))
            universal_pre.append(pre_i)
            G = g_universal
            if (verbose) :
                print(f"\n[build_G] i={i}, chose UNIVERSAL, G={G}")
                print_stack(stack)
            i += 1

        else:
            # Universal branch failed; attempt existential branch: G ∧ E(ψ_i)
            g_existential = astkh.And(G, astkh.Diamond(post_i))
            z3_model = s5solver.get_model(g_existential)
            result = z3_model.check()
            if result == sat:
                stack.append(("existential", i, G))
                M.append(pair_i)
                G = g_existential
                if (verbose) :
                    print(f"\n[build_G] i={i}, chose EXISTENTIAL, G={G}")
                    print_M(M)
                    print_stack(stack)
                i += 1

            else:
                # Both choices failed for current formula; invoke backtracking
                if (verbose) :
                    print(f"\n[build_G] i={i}, both UNSAT, invoking backtracking...")
                status, G_new, M_new, universal_pre_new = backtracking(G, M, universal_pre, stack, positives)
                if status == "UNSAT":
                    return "UNSAT"
                else:
                    G = G_new
                    M = M_new
                    universal_pre = universal_pre_new
                    i = status + 1

    # Successfully constructed G for all positive clauses
    if (verbose) :
        print(f"\n[build_G] Finished. Final G={G}")
        print_M(M)
        print_stack(stack)
    return G, M, universal_pre, stack

def get_pre_post_conditions(M):
    """
    Extracts unique preconditions and postconditions from active existential choices in M.
    """

    M_pre = []
    M_post = []
    for (pre, post) in M:
        if pre not in M_pre:
            M_pre.append(pre)
        if post not in M_post:
            M_post.append(post)
    return M_pre, M_post

def build_matrix(M, M_pre, M_post):
    """
    Initializes the matrix representation M_x mapping preconditions to postconditions.
    """

    M_x = {}
    for pre in M_pre:
        M_x[str(pre)] = {}
        for post in M_post:
            M_x[str(pre)][str(post)] = None

    # Mark cells corresponding to active existential choices in M as True
    for (pre, post) in M:
        M_x[str(pre)][str(post)] = True
    return M_x

def complete_matrix(G, M, M_pre, M_post, M_x):
    """
    Completes matrix M_x by computing semantic implications under G
    and transitively propagating reachability via a worklist queue.
    """

    # Step 1: 
    # For each postcondition ψ, find which preconditions φ it semantically implies under G (i.e., G |= A(ψ -> φ))
    implies = {}
    for psi in M_post:
        implies[str(psi)] = []
        for phi in M_pre:
            g_check = astkh.And(G, astkh.Diamond(astkh.And(psi, astkh.Not(phi))))
            z3_model = s5solver.get_model(g_check)
            result = z3_model.check()
            if result != sat:
                implies[str(psi)].append(phi)

    # Step 2: Initialize and fill depends map
    depends = {}
    for phi in M_pre:
        depends[str(phi)] = set()

    for phi in M_pre:
        for psi in M_post:
            if M_x[str(phi)][str(psi)] == True:
                for phi_prima in implies[str(psi)]:
                    depends[str(phi_prima)].add(str(phi))

    # Step 3: Propagate transitive reachability
    str_to_formula = {str(phi): phi for phi in M_pre}
    pending_deque = deque(str(phi) for phi in M_pre)
    pending_set = set(str(phi) for phi in M_pre)

    while pending_deque:
        phi_str = pending_deque.popleft()
        pending_set.discard(phi_str)
        phi = str_to_formula[phi_str]

        for psi in M_post:
            if M_x[str(phi)][str(psi)] == True:
                for phi_prima in implies[str(psi)]:
                    for psi_prima in M_post:
                        if M_x[str(phi_prima)][str(psi_prima)] == True:
                            if M_x[str(phi)][str(psi_prima)] != True:
                                M_x[str(phi)][str(psi_prima)] = True
                                for dep_str in depends[phi_str]:
                                    if dep_str not in pending_set:
                                        pending_deque.append(dep_str)
                                        pending_set.add(dep_str)
                                for phi_segunda in implies[str(psi_prima)]:
                                    phi_segunda_str = str(phi_segunda)
                                    if phi_str not in depends[phi_segunda_str]:
                                        depends[phi_segunda_str].add(phi_str)

    return M_x

def check_negatives(negatives, G, M_pre, M_post, M_x, stack, positives, M, universal_pre):
    """
    Validates negative formulas ~Kh(φ_i, ψ_i) against current choices in G and matrix M_x.

    Checks whether universal preconditions in G or an active witness plan in M_x 
    prove kh(φ_i, ψ_i), contradicting the required negative ~kh(φ_i, ψ_i).
    """

    for nkh in negatives:
        phi = nkh.left
        psi = nkh.right

        if (verbose) :
            print(f"\n[check_negatives] Processing ~Kh({phi}, {psi})")
        
        # Step 0: check universal_pre_new
        for alpha in universal_pre:
            g_check = astkh.And(G, astkh.Diamond(astkh.And(phi, astkh.Not(alpha))))
            z3_model = s5solver.get_model(g_check)
            result = z3_model.check()
            if result != sat:
                j, G_new, M_new, universal_pre_new = backtracking(G, M, universal_pre, stack, positives)
                if j == "UNSAT":
                    return "UNSAT"
                else:
                    return j, G_new, M_new, universal_pre_new

        # Step 1: find problematic posts
        post_prob = []
        for beta in M_post:
            g_check = astkh.And(G, astkh.Diamond(astkh.And(beta, astkh.Not(psi))))
            z3_model = s5solver.get_model(g_check)
            result = z3_model.check()
            if result != sat:
                post_prob.append(beta)

        if (verbose) :
            print(f"  post_prob: {[str(b) for b in post_prob]}")

        if not post_prob:
            if (verbose) :
                print("  No problematic posts, this negative is safe.")
            continue

        # Step 2: find problematic pres
        pre_prob = []
        for alpha in M_pre:
            g_check = astkh.And(G, astkh.Diamond(astkh.And(phi, astkh.Not(alpha))))
            z3_model = s5solver.get_model(g_check)
            result = z3_model.check()
            if result != sat:
                pre_prob.append(alpha)

        if (verbose) :
            print(f"  pre_prob: {[str(a) for a in pre_prob]}")

        if not pre_prob:
            if (verbose) :
                print("  No problematic pres, this negative is safe.")
            continue

        # Step 3: check path in matrix
        for alpha in pre_prob:
            for beta in post_prob:
                if M_x[str(alpha)][str(beta)] == True:
                    if (verbose) :
                        print(f"  Dangerous path found: M_x[{alpha}][{beta}] = T, invoking backtracking...")
                    j, G_new, M_new, universal_pre_new = backtracking(G, M, universal_pre, stack, positives)
                    if j == "UNSAT":
                        return "UNSAT"
                    else:
                        return j, G_new, M_new, universal_pre_new

    return "SAT"

def solver(problem):
    assert isinstance(problem, astkh.Clauses)
    start_time = time.perf_counter()

    positives = [form for form in problem.clauses if isinstance(form, astkh.Kh)]
    negatives = [form for form in problem.clauses if isinstance(form, astkh.NKh)]

    G = astkh.Top()
    M = []
    universal_pre = []
    stack = []
    pos = 0

    # if there is no negative forms we have to check only the positive ones
    if (negatives == []) :
        first_and = astkh.Top()
        # now we compute the big conjunction:  
        for f in positives :
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

        else:
            end_time = time.perf_counter()
            print("The formula is UNSAT.")
            print(f"Time: {str(end_time - start_time)} seconds.")
            return

    # if there is no positive forms we have to check only the negative ones
    if (positives == []) :
        second_and = astkh.Top()
        # now we compute the big conjunction:  
        for f in negatives :
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
        else:
            end_time = time.perf_counter()
            print("The formula is UNSAT.")
            print(f"Time: {str(end_time - start_time)} seconds.")
            return

    # there are positive and negative atoms
    # First, check SAT for Θ+ ∧ Θ- 
    first_and = astkh.Top()
    for f in positives :
        first_and = astkh.And(first_and, astkh.Or(astkh.Box(astkh.Not(f.left)), astkh.Diamond(f.right)))
    second_and = astkh.Top()
    for f in negatives :
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


    while True:
        print(f"\n[solver] Calling build_G from pos={pos}")
        result = build_G(positives, pos, G, M, universal_pre, stack)

        if result == "UNSAT":
            end_time = time.perf_counter()
            print("The formula is UNSAT.")
            print(f"Time: {str(end_time - start_time)} seconds.")
            return "UNSAT"
        else:
            G, M, universal_pre_new, stack = result

        M_pre, M_post = get_pre_post_conditions(M)
        M_x = build_matrix(M, M_pre, M_post)
        M_x = complete_matrix(G, M, M_pre, M_post, M_x)

        if (verbose) :
            print("\n[solver] Matrix after complete_matrix:")
            print_matrix(M_x, M_pre, M_post)

        result = check_negatives(negatives, G, M_pre, M_post, M_x, stack, positives, M, universal_pre_new)

        if result == "SAT":
            end_time = time.perf_counter()
            print("The formula is SAT.")
            print(f"Time: {str(end_time - start_time)} seconds.")
            return "SAT"

        elif result == "UNSAT":
            end_time = time.perf_counter()
            print("The formula is UNSAT.")
            print(f"Time: {str(end_time - start_time)} seconds.")
            return "UNSAT"

        else:
            status, G, M, universal_pre = result
            pos = status + 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    file = ""
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-f", "--file", dest="file", type=validate_file,
                        help="the file with the formula", metavar="FILE")
    parser.add_argument("-i", "--inline", dest="form", help="takes a formula as inline input", metavar="FORMULA")
    args = parser.parse_args()

    if args.verbose:
        verbose = True
    if args.form:
        problem = args.form
        parsed_form = khparser.parse(problem)
        solver(parsed_form)
    elif args.file:
        file_name = args.file
        with open(file_name, "r") as file:
            problem = file.read()
            parsed_form = khparser.parse(problem)
            solver(parsed_form)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)