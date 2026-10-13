"""
Optimized DCC Module with Dual-Path Execution.
- Fast syntactic literal conflict checking for d = 1.
- Exact upper bound fallback for d >= 2.
"""

import S5.AST_S5 as ast


def has_nested_modalities(node, inside_modal=False):
    if node is None:
        return False
    if isinstance(node, (ast.Box, ast.Diamond)):
        if inside_modal:
            return True
        return has_nested_modalities(node.operand, inside_modal=True)
    elif isinstance(node, ast.Not):
        return has_nested_modalities(node.operand, inside_modal)
    elif isinstance(node, (ast.And, ast.Or)):
        return has_nested_modalities(node.left, inside_modal) or has_nested_modalities(
            node.right, inside_modal
        )
    return False


def count_effective_diamonds(node):
    """
    Counts unique/effective Diamond requirements in the AST 
    to avoid over-estimating W in modal depth d >= 2.
    """
    seen_diamonds = set()

    def traverse(curr):
        if curr is None:
            return
        if isinstance(curr, ast.Diamond):
            # Key by string representation to deduplicate identical modal requirements
            repr_str = str(curr.operand)
            seen_diamonds.add(repr_str)
            traverse(curr.operand)
        elif isinstance(curr, ast.Box):
            traverse(curr.operand)
        elif isinstance(curr, ast.Not):
            traverse(curr.operand)
        elif isinstance(curr, (ast.And, ast.Or)):
            traverse(curr.left)
            traverse(curr.right)

    traverse(node)
    return len(seen_diamonds)


def extract_modals(node):
    diamonds = []
    top_level_boxes = []

    def traverse_diamonds(curr):
        if curr is None:
            return
        if isinstance(curr, ast.Diamond):
            diamonds.append(curr)
        elif isinstance(curr, ast.Box):
            traverse_diamonds(curr.operand)
        elif isinstance(curr, ast.Not):
            traverse_diamonds(curr.operand)
        elif isinstance(curr, (ast.And, ast.Or)):
            traverse_diamonds(curr.left)
            traverse_diamonds(curr.right)

    traverse_diamonds(node)

    def traverse_top_boxes(curr):
        if curr is None:
            return
        if isinstance(curr, ast.Box):
            top_level_boxes.append(curr)
        elif isinstance(curr, ast.And):
            traverse_top_boxes(curr.left)
            traverse_top_boxes(curr.right)

    traverse_top_boxes(node)

    return diamonds, top_level_boxes


def get_literals_fast(node):
    """Extrae literales de forma ultrarrápida para fórmulas d=1."""
    if isinstance(node, ast.Var):
        return {node.name: True}
    elif isinstance(node, ast.Not) and isinstance(node.operand, ast.Var):
        return {node.operand.name: False}
    elif isinstance(node, ast.And):
        l1 = get_literals_fast(node.left)
        l2 = get_literals_fast(node.right)
        res = dict(l1)
        res.update(l2)
        return res
    return {}


def dsatur_coloring(nodes, edges):
    if not nodes:
        return {}, 0

    colors = {}
    degree = {v: len(edges[v]) for v in nodes}
    saturation = {v: set() for v in nodes}
    uncolored = set(nodes)

    while uncolored:
        best_node = None
        max_sat = -1
        max_deg = -1

        for v in uncolored:
            sat_len = len(saturation[v])
            deg = degree[v]
            if sat_len > max_sat or (sat_len == max_sat and deg > max_deg):
                max_sat = sat_len
                max_deg = deg
                best_node = v

        neighbor_colors = saturation[best_node]
        color = 1
        while color in neighbor_colors:
            color += 1

        colors[best_node] = color
        uncolored.remove(best_node)

        for neighbor in edges[best_node]:
            if neighbor in uncolored:
                saturation[neighbor].add(color)
                degree[neighbor] -= 1

    chromatic_number = max(colors.values()) if colors else 0
    return colors, chromatic_number


def compute_dcc_worlds(nnf_root):
    # 1. Fallback exacto para d >= 2
    # Deduplicated upper bound fallback for d >= 2
    if has_nested_modalities(nnf_root):
        eff_d = count_effective_diamonds(nnf_root)
        return eff_d + 1, {}

    # 2. Fast-Path para d = 1 (Extracción e intersección sintáctica Pura)
    diamonds, top_boxes = extract_modals(nnf_root)
    if not diamonds:
        return 1, {}

    # Extraer restricciones de cajas top-level
    box_constraints = {}
    for box in top_boxes:
        lits = get_literals_fast(box.operand)
        box_constraints.update(lits)

    # Extraer literales de diamantes
    diamond_lits = [get_literals_fast(d.operand) for d in diamonds]

    nodes = list(range(len(diamonds)))
    edges = {i: set() for i in nodes}

    # Detección sintáctica instantánea O(1) por par
    for i in range(len(diamonds)):
        l_i = diamond_lits[i]
        # Conflicto directo con Cajas Top-Level
        i_box_conflict = any(
            var in l_i and l_i[var] != sign for var, sign in box_constraints.items()
        )

        for j in range(i + 1, len(diamonds)):
            l_j = diamond_lits[j]
            j_box_conflict = any(
                var in l_j and l_j[var] != sign
                for var, sign in box_constraints.items()
            )

            # Conflicto entre los dos diamantes (literales complementarios)
            ij_conflict = any(
                var in l_i and var in l_j and l_i[var] != l_j[var] for var in l_i
            )

            if i_box_conflict or j_box_conflict or ij_conflict:
                edges[i].add(j)
                edges[j].add(i)

    node_colors, chromatic_number = dsatur_coloring(nodes, edges)
    diamond_to_color = {id(diamonds[i]): node_colors[i] for i in nodes}

    dcc_size = chromatic_number + 1
    return dcc_size, diamond_to_color