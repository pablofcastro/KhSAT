import time
import Kh.AST_kh as astkh
import s5_solver as s5solver
from z3 import *

def get_log_file():
    return open(f"solver_log.txt", "w", encoding="utf-8")

def log(f, msg):
    print(msg)
    f.write(msg + "\n")
    f.flush()

def log_matrix(f, M_x, M_pre, M_post):
    log(f, "\n=== Matrix M_x ===")
    header = "\t" + "\t".join(str(post) for post in M_post)
    log(f, header)
    for pre in M_pre:
        row = str(pre) + "\t"
        row += "\t".join("T" if M_x[str(pre)][str(post)] == True else "." for post in M_post)
        log(f, row)
    log(f, "==================\n")

def log_initial_check(log_file, combined_formula, initial_result, verbose=False):
    if not verbose or log_file is None:
        return

    log(log_file, "=" * 60)
    log(log_file, "INITIAL CHECK: theta_pos AND theta_neg")
    log(log_file, f"  Formula: {combined_formula}")
    log(log_file, f"  Result: {'SAT' if initial_result == sat else 'UNSAT'}")
    log(log_file, "=" * 60)

def log_iteration_header(log_file, iteration, pos, verbose=False):
    if not verbose or not log_file:
        return

    log(log_file, "\n" + "=" * 60)
    log(log_file, f"ITERATION {iteration} of main while loop (pos={pos})")
    log(log_file, "=" * 60)

def log_build_g_finished(log_file, G, M, universal_pre, verbose=False):
    if not verbose or log_file is None:
        return

    log(log_file, f"\n[build_G] FINISHED")
    log(log_file, f"  Final G = {G}")
    log(log_file, f"  M = {[(getattr(p.name, 'value', str(p.name)), getattr(q.name, 'value', str(q.name))) for p, q in M]}")
    log(log_file, f"  universal_pre = {[(getattr(getattr(alpha, 'name', alpha), 'value', str(alpha)), indices) for (alpha, indices) in universal_pre]}")

def log_problematics_found(log_file, map_prob, verbose=False):
    if not verbose or not log_file:
        return

    log(log_file, f"[get_problematics] Problematic pairs found:")
    for key, (pre_prob, post_prob) in map_prob.items():
        log(log_file, f"  ~Kh({getattr(getattr(key[0], 'name', key[0]), 'value', str(key[0]))}, {getattr(getattr(key[1], 'name', key[1]), 'value', str(key[1]))}):")
        log(log_file, f"    pre_prob  = {[getattr(getattr(a, 'name', a), 'value', str(a)) for a in pre_prob]}")
        log(log_file, f"    post_prob = {[getattr(getattr(b, 'name', b), 'value', str(b)) for b in post_prob]}")

def log_backtrack(log_file, source, pos, G, M, universal_pre, forced_existential=None, verbose=False):
    if not verbose:
        return
    log(log_file, f"[{source}] BACKTRACK to pos={pos}")
    log(log_file, f"  New G after backtrack = {G}")
    log(log_file, f"  New M = {[(str(p), str(q)) for p, q in M]}")
    log(log_file, f"  New universal_pre = {[(str(alpha), indices) for (alpha, indices) in universal_pre]}")
    if forced_existential is not None:
        log(log_file, f"  forced_existential = {forced_existential}")

def finish_with_log(result, start_time, log_file, msg=None, verbose=False):
    if verbose:
        if msg:
            log(log_file, msg)
        log_file.close()

    end_time = time.perf_counter()

    print(f"The formula is {result}.")
    print(f"Time: {str(end_time - start_time)} seconds.")
    return result

def validate_file(f):
    if not os.path.exists(f):
        raise argparse.ArgumentTypeError(f"Couldn't find {f}.")
    return f

def apply_existential_choice(idx, g_base, g_existential, pair, stack, M, log_file=None, log_msg=None, verbose=False):
    stack.append(("existential", idx, g_base))
    M.append(pair)
    
    if verbose and log_file and log_msg:
        log(log_file, log_msg)
        
    return g_existential


def apply_universal_choice(idx, g_base, g_universal, pre_formula, stack, universal_pre, log_file=None, log_msg=None, verbose=False):
    stack.append(("universal", idx, g_base))
    
    existing = next((entry for entry in universal_pre if str(entry[0]) == str(pre_formula)), None)
    if existing is None:
        universal_pre.append((pre_formula, [idx]))
    elif idx not in existing[1]:
        existing[1].append(idx)
        
    if verbose and log_file and log_msg:
        log(log_file, log_msg)
        
    return g_universal

def build_theta_pos(positives, log_file, verbose=False):
    # Θ+
    first_and = astkh.Top()
    for f in positives:
        first_and = astkh.And(first_and, astkh.Or(astkh.Box(astkh.Not(f.left)), astkh.Diamond(f.right)))
    
    return first_and

def build_theta_neg(negatives, log_file, verbose=False):
    # Θ-
    second_and = astkh.Top()
    for f in negatives:
        second_and = astkh.And(second_and, astkh.Diamond(astkh.And(f.left, astkh.Not(f.right))))
    
    return second_and

def solve_and_print(formula, start_time, verbose=False):

    if verbose:
        print(formula)
        
    z3_model = s5solver.get_model(formula)
    result = z3_model.check()
    end_time = time.perf_counter()
    
    if result == sat:
        print("The formula is SAT.")
        if verbose:
            print("Model:")
            print(z3_model.model())
    else:
        print("The formula is UNSAT.")
        
    print(f"Time: {str(end_time - start_time)} seconds.")
    return result