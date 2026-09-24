import Kh.AST_kh as astkh
import s5_solver as s5solver
import time
from z3 import *
import argparse, os
import Kh.parser_kh as khparser
from collections import deque
import datetime
from logger_and_extra_incremental import *

verbose = False

def backtracking(G, M, universal_pre, stack, positives, forced_existential, target_idx=None):
    """
    Performs backtracking over the positive formulas' decision tree (Kh(A_j, B_j) = Box(~A_j) v Diamond(B_j)).
    
    Unwinds the stack to find the last 'universal' choice, attempts to switch it to 
    'existential', and checks S5-satisfiability with Z3. If valid, updates state (G, M) 
    to resume; otherwise, continues popping or returns UNSAT if exhausted.
    
    If target_idx is provided, it skips attempting existential branches for any j > target_idx
    to effectively backjump directly to target_idx.
    """
    
    while stack:
        type, j, g_prev = stack.pop()
        kh = positives[j]
        pre_j = kh.left
        post_j = kh.right
        pair_j = (pre_j, post_j)

        if (type == "universal"):
            # Remove j from the (alpha, [indices]) entry; delete entry if list becomes empty
            existing = next((entry for entry in universal_pre if str(entry[0]) == str(pre_j)), None)
            if existing is not None:
                if j in existing[1]:
                    existing[1].remove(j)
                if not existing[1]:
                    universal_pre.remove(existing)

            if target_idx is not None and j > target_idx:
                # We want to backjump further down; skip trying existential here
                continue

            g_existential = astkh.And(g_prev, astkh.Diamond(post_j))
            z3_model = s5solver.get_model(g_existential)
            result = z3_model.check()
            if result == sat:
                G = apply_existential_choice(j, g_prev, g_existential, pair_j, stack, M)
                return j, G, M, universal_pre
        else:
            M.pop()

    return "UNSAT", None, None, None

def build_G(positives, pos, G, M, universal_pre, stack, log_file, forced_existential=None, verbose=False):
    """
    Iteratively processes positive formulas from index `pos` to construct the global formula G.

    For each clause Kh(A_i, B_i), it attempts the universal choice Box(~A_i) first.
    If unsatisfiable, it attempts the existential choice Diamond(B_i). If both fail,
    it invokes backtracking to unwind previous choices and find a satisfiable state.
    """
    if verbose: 
        log(log_file, f"\n[build_G] Starting from pos={pos}, current G={G}")

    if forced_existential is None:
        forced_existential = []

    length_positives = len(positives)
    i = pos

    while (i < length_positives):
        kh = positives[i] #kh(φ_i, ψ_i)
        pre_i = kh.left
        post_i = kh.right
        pair_i = (pre_i, post_i)

        if i in forced_existential:
            # This atom is forced to be existential; skip the universal branch entirely
            if verbose: log(log_file, f"  [build_G] i={i} Kh({pre_i},{post_i}) -> FORCED EXISTENTIAL")

            g_existential = astkh.And(G, astkh.Diamond(post_i))
            z3_model = s5solver.get_model(g_existential)
            result = z3_model.check()

            if result == sat:
                G = apply_existential_choice(i, G, g_existential, pair_i, stack, M, log_file, f"    -> SAT, G={g_existential}", verbose)
                i += 1
            else:
                # Forced existential UNSAT; backtrack
                if verbose: log(log_file, f"    -> UNSAT even as forced existential, backtracking...")
                
                status, G_new, M_new, universal_pre_new = backtracking(G, M, universal_pre, stack, positives, forced_existential)

                if status == "UNSAT":
                    return "UNSAT", None, None, None, None, None
                else:
                    if verbose: log(log_file, f"  [build_G] backtrack to j={status}, new G={G_new}")
                    G = G_new
                    M = M_new
                    universal_pre = universal_pre_new
                    i = status + 1

        else:
            # Attempt universal branch: G ∧ A(~ φ_i)
            g_universal = astkh.And(G, astkh.Box(astkh.Not(pre_i)))
            z3_model = s5solver.get_model(g_universal)
            result = z3_model.check()
            if result == sat:
                G = apply_universal_choice(i, G, g_universal, pre_i, stack, universal_pre, log_file, f"  [build_G] i={i} Kh({pre_i},{post_i}) -> UNIVERSAL, G={g_universal}", verbose)
                i += 1

            else:
                # Universal branch failed; attempt existential branch: G ∧ E(ψ_i)
                g_existential = astkh.And(G, astkh.Diamond(post_i))
                z3_model = s5solver.get_model(g_existential)
                result = z3_model.check()
                if result == sat:
                    G = apply_existential_choice(i, G, g_existential, pair_i, stack, M, log_file, f"  [build_G] i={i} Kh({pre_i},{post_i}) -> EXISTENTIAL, G={g_existential}", verbose)
                    i += 1

                else:
                    # Both choices failed for current formula; invoke backtracking
                    if (verbose): log(log_file, f"  [build_G] i={i} Kh({pre_i},{post_i}) -> both UNSAT, backtracking...")
                    status, G_new, M_new, universal_pre_new = backtracking(G, M, universal_pre, stack, positives, forced_existential)
                    if status == "UNSAT":
                        return "UNSAT", None, None, None, None, None
                    else:
                        if (verbose) :
                            log(log_file, f"  [build_G] backtrack to j={status}, new G={G_new}")
                        G = G_new
                        M = M_new
                        universal_pre = universal_pre_new
                        i = status + 1

    # Successfully constructed G for all positive clauses
    if (verbose) :
        log(log_file, f"\n[build_G] Finished. Final G={G}")

    return "OK", G, M, universal_pre, stack, forced_existential

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

def get_problematics(negatives, M_pre, M_post, G, log_file, verbose=False):
    """
    Evaluates problematic pre and post-conditions for negative formulas.

    """
    if verbose:
        log(log_file, f"\n[get_problematics] Starting")
    map_prob = {}

    for nkh in negatives:
        phi = nkh.left
        psi = nkh.right
        
        key = (str(phi), str(psi))

        if verbose:
            phi_str = getattr(getattr(phi, 'name', phi), 'value', str(phi))
            psi_str = getattr(getattr(psi, 'name', psi), 'value', str(psi))
            log(log_file, f"\n[get_problematics] Processing ~Kh({phi_str}, {psi_str})")

        # Step 1: Problematic pre-conditions analysis
        pre_prob = []
        for alpha in M_pre:
            g_check = astkh.And(G, astkh.Diamond(astkh.And(phi, astkh.Not(alpha))))
            z3_model = s5solver.get_model(g_check)
            if z3_model.check() != sat:
                pre_prob.append(alpha)

        if verbose:
            log(log_file, f"  pre_prob: {[getattr(getattr(a, 'name', a), 'value', str(a)) for a in pre_prob]}")

        # Early exit
        if not pre_prob:
            if verbose:
                log(log_file, "  No problematic pres, skipping post analysis for this negative.")
            continue

        # Step 2: Problematic post-conditions analysis
        post_prob = []
        for beta in M_post:
            g_check = astkh.And(G, astkh.Diamond(astkh.And(beta, astkh.Not(psi))))
            z3_model = s5solver.get_model(g_check)
            if z3_model.check() != sat:
                post_prob.append(beta)

        if verbose:
            log(log_file, f"  post_prob: {[getattr(getattr(b, 'name', b), 'value', str(b)) for b in post_prob]}")

        # Early exit
        if not post_prob:
            if verbose:
                log(log_file, "  No problematic posts for this negative.")
            continue


        map_prob[key] = (pre_prob, post_prob)

    return map_prob if map_prob else "SAT"

def check_universal_preconditions(negatives, G, M, universal_pre, stack, positives, pos, log_file, forced_existential=None, verbose=False, skip_optimization= False):
    """
    Checks if universal preconditions in universal_pre are compatible with the negative formulas under G.
    """

    if verbose: 
        log(log_file, f"\n[check_universal_preconditions] Starting")

    if forced_existential is None:
        forced_existential = []

    for idx_neg, nkh in enumerate(negatives):
        phi = nkh.left
        phi_clean = getattr(phi, 'value', str(phi))
        
        for idx_pre, (alpha, alpha_indices) in enumerate(universal_pre):
            alpha_clean = getattr(alpha, 'value', str(alpha))
            
            g_check = astkh.And(G, astkh.Diamond(astkh.And(phi, astkh.Not(alpha))))

            if verbose: 
                log(log_file, f"  Checking negatives[{idx_neg}] = {phi_clean}, universal_pre[{idx_pre}] = {alpha_clean} | G /\\ E({phi_clean} /\\ ~{alpha_clean})")
            
            z3_model = s5solver.get_model(g_check)
            result = z3_model.check()
            if verbose: 
                log(log_file, f"    Result: {'SAT' if result == sat else 'UNSAT'}")
            
            if result != sat:
                # Register all positive indices that had alpha as universal precondition as forced existential
                if(skip_optimization):
                    forced_existential = None
                    target_idx = None
                else:
                    for fi in alpha_indices:
                        if fi not in forced_existential:
                            forced_existential.append(fi)
                    target_idx = min(alpha_indices)                    

                if verbose: 
                    log(log_file, f"  -> Conflict detected: ({phi_clean}) implies ({alpha_clean})")
                    log(log_file, f"     Forced existential: {forced_existential}, backjumping to <= {target_idx}")

                backtrack_res = backtracking(G, M, universal_pre, stack, positives, forced_existential, target_idx)

                if backtrack_res[0] == "UNSAT":
                    return "UNSAT", None, None, None, None, forced_existential
                else:
                    j, G_new, M_new, universal_pre_new = backtrack_res
                    return "BACKTRACK", G_new, M_new, universal_pre_new, j + 1, forced_existential
                    
    return "OK", G, M, universal_pre, pos, forced_existential

def build_matrix(M, M_pre, M_post, log_file, verbose=False):
    """
    Initializes the matrix representation M_x mapping preconditions to postconditions.
    """

    if verbose:
        log(log_file, f"\n[build_matrix] Starting")

    M_x = {}
    for pre in M_pre:
        M_x[str(pre)] = {}
        for post in M_post:
            M_x[str(pre)][str(post)] = None

    # Mark cells corresponding to active existential choices in M as True
    for (pre, post) in M:
        M_x[str(pre)][str(post)] = True
    return M_x

def complete_matrix(G, M, M_pre, M_post, M_x, log_file, verbose=False):
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

    if (verbose) :
        log(log_file, "[complete_matrix] Matrix after completion:")
        log_matrix(log_file, M_x, M_pre, M_post)

    return M_x

def check_negatives(negatives, G, M_x, stack, positives, M, universal_pre, map_prob, log_file, forced_existential=None, verbose=False):
    """
    Validates negative formulas ~Kh(φ_i, ψ_i) against current choices in G and matrix M_x.
    """
    if verbose:
        log(log_file, f"\n[check_negatives] Starting")

    if forced_existential is None:
        forced_existential = []
    for nkh in negatives:
        phi = nkh.left
        psi = nkh.right

        if verbose:
            phi_str = getattr(getattr(phi, 'name', phi), 'value', str(phi))
            psi_str = getattr(getattr(psi, 'name', psi), 'value', str(psi))
            log(log_file, f"\n[check_negatives] Processing ~Kh({phi_str}, {psi_str})")

        # Check path in matrix using problematics map

        key = (str(phi), str(psi))
        prob_pair = map_prob.get(key)
        
        if prob_pair is None:
            if verbose: 
                log(log_file, f"  ~Kh({phi},{psi}) -> no problematic pairs, skipping")
            continue

        pre_prob, post_prob = prob_pair

        for alpha in pre_prob:
            alpha_str = str(alpha)
            row = M_x.get(alpha_str)
            if not row:
                continue
                
            for beta in post_prob:
                if row.get(str(beta)) is True:
                    if verbose: 
                        log(log_file, f"  ~Kh({phi},{psi}) -> CONFLICT at M_x[{alpha}][{beta}] = T")
                        log(log_file, f"    This means Kh({phi},{psi}) is forced true, backtracking...")
                    j, G_new, M_new, universal_pre_new = backtracking(G, M, universal_pre, stack, positives, forced_existential)
                    if j == "UNSAT":
                        return "UNSAT"
                    else:
                        return j, G_new, M_new, universal_pre_new, forced_existential

    return "SAT"

def complete_and_check_matrix(G, M, M_pre, M_post, M_x, negatives, map_prob, stack, positives, universal_pre, log_file, forced_existential=None, verbose=False):
    if verbose:
        log(log_file, "\n[complete_and_check_matrix] Starting")

    if forced_existential is None:
        forced_existential = []

    str_to_post = {str(psi): psi for psi in M_post}

    implies_cache = {}
    depends = {str(phi): set() for phi in M_pre}

   # collect all conflict pairs
    active_conflict_pairs = {}
    for nkh in negatives:
        key = (str(nkh.left), str(nkh.right))
        prob_pair = map_prob.get(key)
        if prob_pair:
            pre_prob, post_prob = prob_pair
            for alpha in pre_prob:
                for beta in post_prob:
                    active_conflict_pairs[(str(alpha), str(beta))] = nkh


    # checks for conflicts in a pair (phi_str, psi_str) and triggers backtracking if one is found.
    def check_conflict(phi_str, psi_str):
        pair = (phi_str, psi_str)
        if pair in active_conflict_pairs:
            if verbose:
                log(log_file, f" CONFLICT DETECTED at M_x[{phi_str}][{psi_str}] = T")
            j, G_new, M_new, universal_pre_new = backtracking(G, M, universal_pre, stack, positives, forced_existential)
            if j == "UNSAT":
                return ("CONFLICT", "UNSAT")
            else:
                return ("CONFLICT", (j, G_new, M_new, universal_pre_new, forced_existential))
        return ("OK", None)

    # check for pre-existing conflicts in the matrix.
    for (alpha_str, beta_str), nkh in active_conflict_pairs.items():
        if M_x.get(alpha_str, {}).get(beta_str) is True:
            if verbose:
                log(log_file, f" CONFLICT PRE-EXISTING at M_x[{alpha_str}][{beta_str}] = T")
            status, result = check_conflict(alpha_str, beta_str)
            if status == "CONFLICT":
                return result

    # initialize the queue with pre-problematic and their post
    queue = deque()
    in_queue = set()

    all_pre_prob_str = {alpha_str for (alpha_str, _) in active_conflict_pairs.keys()}

    # search in M_x to find which post alpha_str reaches. Potential dangerous paths.
    for alpha_str in all_pre_prob_str:
        if alpha_str in M_x:
            for psi_str, is_active in M_x[alpha_str].items():
                if is_active is True:
                    item = (alpha_str, psi_str)
                    if item not in in_queue:
                        queue.append(item)
                        in_queue.add(item)

    # transitive propagation loop
    while queue:
        phi_orig_str, psi_str = queue.popleft() #acá saco una pre problematica, junto a una post que llega
        in_queue.discard((phi_orig_str, psi_str))

        psi = str_to_post[psi_str]

        for phi_prima in M_pre:
            phi_prima_str = str(phi_prima)

            # query Z3 lazily
            # given the post-condition of a problematic pre-condition, we examine one by one which pre-condition it implies.
            pair_key = (psi_str, phi_prima_str)
            if pair_key not in implies_cache:
                g_check = astkh.And(G, astkh.Diamond(astkh.And(psi, astkh.Not(phi_prima))))
                z3_model = s5solver.get_model(g_check)
                implies_cache[pair_key] = (z3_model.check() != sat)

            # We continue because for the moment there is no dangerous path, let's see another pre
            if not implies_cache[pair_key]:
                continue

            # Register dependency
            depends[phi_prima_str].add(phi_orig_str)

            # See where phi_prime ends up in the matrix.
            for psi_new_str, is_reachable in M_x[phi_prima_str].items():
                if is_reachable is not True:
                    continue

                # Actualizar alcanzabilidad transitiva para phi_orig
                if M_x[phi_orig_str][psi_new_str] != True:
                    M_x[phi_orig_str][psi_new_str] = True

                    # Chequear conflicto para phi_orig
                    status, result = check_conflict(phi_orig_str, psi_new_str)
                    if status == "CONFLICT":
                        return result

                    # Encolar para continuar exploración desde phi_orig
                    new_item = (phi_orig_str, psi_new_str)
                    if new_item not in in_queue:
                        queue.append(new_item)
                        in_queue.add(new_item)

                # Propagate to dependents of phi_orig: 
                # if phi_orig now reaches psi_new, all those that depended on phi_orig also reach psi_new. 
                # We also enqueue them so they continue exploring from psi_new.
                for dep_phi_str in depends[phi_orig_str]:
                    if M_x[dep_phi_str][psi_new_str] != True:
                        M_x[dep_phi_str][psi_new_str] = True

                        # Check for conflict for dep_phi
                        status, result = check_conflict(dep_phi_str, psi_new_str)
                        if status == "CONFLICT":
                            return result

                        # Encolar dep_phi para continuar exploración transitiva
                        #dep_item = (dep_phi_str, psi_new_str)
                        #if dep_item not in in_queue:
                        #    queue.append(dep_item)
                        #    in_queue.add(dep_item)

                        # Only enqueue if dep_phi_str is a problematic precondition
                        if dep_phi_str in all_pre_prob_str:
                            dep_item = (dep_phi_str, psi_new_str)
                            if dep_item not in in_queue:
                                queue.append(dep_item)
                                in_queue.add(dep_item)

    if verbose:
        log(log_file, "[complete_and_check_matrix] Matrix complete without conflicts.")
        log_matrix(log_file, M_x, M_pre, M_post)

    return "SAT"

def solver(problem, verbose=False):
    assert isinstance(problem, astkh.Clauses)
    start_time = time.perf_counter()

    log_file = get_log_file() if verbose else None

    positives = [form for form in problem.clauses if isinstance(form, astkh.Kh)]
    negatives = [form for form in problem.clauses if isinstance(form, astkh.NKh)]

    G = astkh.Top()
    M = []
    universal_pre = []
    stack = []
    forced_existential = []
    pos = 0

    # if there is no negative forms we have to check only the positive ones
    if (negatives == []) :
        theta_pos = build_theta_pos(positives, log_file, verbose)
        if verbose:
            log(log_file, f"\n[ONLY POSITIVES] theta_pos = {theta_pos}")
            log_file.close()
        solve_and_print(theta_pos, start_time, verbose)
        return

    # if there is no positive forms we have to check only the negative ones
    if (positives == []) :
        theta_neg = build_theta_neg(negatives, log_file, verbose)
        if verbose:
            log(log_file, f"\n[ONLY NEGATIVES] theta_neg = {theta_neg}")
            log_file.close()
        solve_and_print(theta_neg, start_time, verbose)
        return

    # there are positive and negative atoms
    # First, check SAT for Θ+ ∧ Θ- 
    theta_pos = build_theta_pos(positives, log_file, verbose)
    theta_neg = build_theta_neg(negatives, log_file, verbose)
    combined_formula = astkh.And(theta_pos, theta_neg)

    z3_model = s5solver.get_model(combined_formula)
    initial_result = z3_model.check()

    log_initial_check(log_file, combined_formula, initial_result, verbose)

    if initial_result != sat:
        return finish_with_log("UNSAT", start_time, log_file, "Formula: theta /\\ theta' is unsat\nRest of formulas unprocessed.")

    #empieza el main loop
    iteration = 0
    while True:
        iteration += 1
        log_iteration_header(log_file, iteration, pos, verbose)

        status, G, M, universal_pre, stack, forced_existential = build_G(positives, pos, G, M, universal_pre, stack, log_file, forced_existential, verbose)

        if status == "UNSAT":
            return finish_with_log("UNSAT", start_time, log_file, "[build_G] Result: UNSAT")

        log_build_g_finished(log_file, G, M, universal_pre, verbose)

        # Validate universal preconditions
        skip_optimization = False
        status, G, M, universal_pre, next_pos, forced_existential = check_universal_preconditions(negatives, G, M, universal_pre, stack, positives, pos, log_file, forced_existential, verbose, skip_optimization)
        
        if status == "UNSAT":
            return finish_with_log("UNSAT", start_time, log_file, "[check_universal_preconditions] Result: UNSAT")
        elif status == "BACKTRACK":
            log_backtrack(log_file, "check_universal_preconditions", next_pos - 1, G, M, universal_pre, verbose)
            pos = next_pos
            continue

        M_pre, M_post = get_pre_post_conditions(M)

        prob_res = get_problematics(negatives, M_pre, M_post, G, log_file, verbose)

        if prob_res == "SAT":
            return finish_with_log("SAT", start_time, log_file, "[get_problematics] No problematic pairs found -> SAT")

        map_prob = prob_res
        log_problematics_found(log_file, map_prob, verbose)

        M_x = build_matrix(M, M_pre, M_post, log_file, verbose)

        #result = complete_and_check_matrix(G, M, M_pre, M_post, M_x, negatives, map_prob, stack, positives, universal_pre, log_file, forced_existential=forced_existential, verbose=verbose)
        M_x = complete_matrix(G, M, M_pre, M_post, M_x, log_file, verbose)

        result = check_negatives(negatives, G, M_x, stack, positives, M, universal_pre, map_prob, log_file, forced_existential, verbose)

        if result in ["SAT", "UNSAT"]:
            return finish_with_log(result, start_time, log_file, f"[check_negatives] Result: {result}")

        else:
            status, G, M, universal_pre, forced_existential = result
            log_backtrack(log_file, "check_negatives", status + 1, G, M, universal_pre, forced_existential, verbose)
            pos = status + 1

    if log_file:
        log_file.close()

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
        solver(parsed_form, verbose)
    elif args.file:
        file_name = args.file
        with open(file_name, "r") as file:
            problem = file.read()
            parsed_form = khparser.parse(problem)
            solver(parsed_form, verbose)
    else:
        parser.print_help(sys.stderr)
        sys.exit(1)