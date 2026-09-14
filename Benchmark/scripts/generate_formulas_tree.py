import os
import random  # Agregado para desordenar aleatoriamente

def generate_tree_kh_relations(m_children: int, n_levels: int):

    if n_levels <= 1:
        return [], []

    relations = []
    current_level_nodes = [("a0", "")]  

    for depth in range(1, n_levels):
        next_level_nodes = []
        for parent_name, current_path in current_level_nodes:
            for children_idx in range(m_children):
                new_path = f"{current_path}_{children_idx}" if current_path else str(children_idx)
                child_name = f"a{depth}_{new_path}"

                relations.append(f"Kh({parent_name},{child_name})")
                next_level_nodes.append((child_name, new_path))

        current_level_nodes = next_level_nodes

    leaf_nodes = [node_name for node_name, _ in current_level_nodes]

    return relations, leaf_nodes


if __name__ == "__main__":
    m = 2  
    n_values = [2, 3, 4, 5, 6]  

    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    project_root = os.path.dirname(script_dir)
    
    output_dir = os.path.join(project_root, 'formulas_tree_shuffled')
    os.makedirs(output_dir, exist_ok=True)

    for n in n_values:
        
        positive_relations, leaves = generate_tree_kh_relations(m_children=m, n_levels=n)
        total_positives = len(positive_relations)
        total_negatives = 1  

        for leaf_index, leaf_node in enumerate(leaves, start=1):
            negative_relation = f"~Kh(a0,{leaf_node})"
            
            # 2. Hacemos una copia y la mezclamos aleatoriamente
            shuffled_positives = positive_relations.copy()
            random.shuffle(shuffled_positives)

            # Concatenamos las relativas positivas ya mezcladas con la negativa al final
            full_formula = shuffled_positives + [negative_relation]
            
            # El nombre del archivo se mantiene exactamente igual
            filename = f"formula{total_positives+1}-{total_positives}-{total_negatives}-leaf-{leaf_index}.kh"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, mode='w', encoding='utf-8', newline='') as f:
                f.write(";".join(full_formula) + "\n")

            print(f"Archivo guardado en: {filepath}")