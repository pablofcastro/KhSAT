import csv
import os
import matplotlib.pyplot as plt
from pathlib import Path

script_dir = os.path.dirname(os.path.abspath(__file__))
graphs_dir = os.path.join(script_dir, 'graphs')

batch_numbers = [1, 2, 3]

incremental_winners = []
basic_opt_winners = []
ties = []

def parse_time(val):
    if str(val).strip().upper() == 'TO':
        return 300.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

for batch in batch_numbers:
    file_incremental = os.path.join(graphs_dir, f'formulas_batch_{batch}_incremental.csv')
    file_basic_opt   = os.path.join(graphs_dir, f'formulas_batch_{batch}_basic_opt.csv')

    if not os.path.exists(file_incremental):
        print(f"Warning: {file_incremental} not found, skipping batch {batch}...")
        continue
    if not os.path.exists(file_basic_opt):
        print(f"Warning: {file_basic_opt} not found, skipping batch {batch}...")
        continue

    # Index by (form, pos, neg) as composite key
    incremental_data = {}
    with open(file_incremental, mode='r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            key = (row['form'], row['pos'], row['neg'])
            incremental_data[key] = row

    basic_opt_data = {}
    with open(file_basic_opt, mode='r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            key = (row['form'], row['pos'], row['neg'])
            basic_opt_data[key] = row

    common_keys = set(incremental_data.keys()) & set(basic_opt_data.keys())
    batch_name = f'batch_{batch}'

    print(f"Batch {batch}: incremental={len(incremental_data)}, basic_opt={len(basic_opt_data)}, common={len(common_keys)}")

    for key in common_keys:
        form, pos, neg = key
        row_inc = incremental_data[key]
        row_bas = basic_opt_data[key]

        t_inc_raw = row_inc['time']
        t_bas_raw = row_bas['time']
        res_inc   = row_inc['result']
        res_bas   = row_bas['result']

        t_inc = parse_time(t_inc_raw)
        t_bas = parse_time(t_bas_raw)

        is_to_inc = str(t_inc_raw).strip().upper() == 'TO'
        is_to_bas = str(t_bas_raw).strip().upper() == 'TO'

        form_label = f"{form}-{pos}-{neg}"

        if is_to_inc and is_to_bas:
            ties.append({
                'category': 'TIE',
                'batch': batch_name,
                'form': form_label,
                'time_basic_opt': t_bas_raw, 'result_basic_opt': res_bas,
                'time_incremental': t_inc_raw, 'result_incremental': res_inc,
                'factor': 1.0
            })
            continue

        if t_inc < t_bas:
            fastest = 'INCREMENTAL WINS'
            ratio = t_bas / t_inc if t_inc > 0 else 1.0
        elif t_bas < t_inc:
            fastest = 'BASIC-OPT WINS'
            ratio = t_inc / t_bas if t_bas > 0 else 1.0
        else:
            fastest = 'TIE'
            ratio = 1.0

        item = {
            'category': fastest,
            'batch': batch_name,
            'form': form_label,
            'time_basic_opt': t_bas_raw, 'result_basic_opt': res_bas,
            'time_incremental': t_inc_raw, 'result_incremental': res_inc,
            'factor': ratio
        }

        if ratio >= 2.0:
            if fastest == 'INCREMENTAL WINS':
                incremental_winners.append(item)
            elif fastest == 'BASIC-OPT WINS':
                basic_opt_winners.append(item)
            else:
                ties.append(item)
        else:
            item['category'] = 'TIE'
            ties.append(item)

# Sort by factor descending
incremental_winners.sort(key=lambda x: x['factor'], reverse=True)
basic_opt_winners.sort(key=lambda x: x['factor'], reverse=True)
ties.sort(key=lambda x: x['factor'], reverse=True)

# Export consolidated CSV
Path(graphs_dir).mkdir(parents=True, exist_ok=True)
output_csv = os.path.join(graphs_dir, 'classified_consolidated.csv')

fieldnames = [
    'category', 'batch', 'form',
    'time_basic_opt', 'result_basic_opt',
    'time_incremental', 'result_incremental',
    'factor'
]

with open(output_csv, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    def write_rows(rows_list):
        for elem in rows_list:
            writer.writerow({
                'category':           elem['category'],
                'batch':              elem['batch'],
                'form':               elem['form'],
                'time_basic_opt':     elem['time_basic_opt'],
                'result_basic_opt':   elem['result_basic_opt'],
                'time_incremental':   elem['time_incremental'],
                'result_incremental': elem['result_incremental'],
                'factor':             f"{elem['factor']:.2f}x"
            })

    write_rows(incremental_winners)
    write_rows(basic_opt_winners)
    write_rows(ties)

print(f"[OK] Consolidated CSV saved at: '{output_csv}'")
print(f"     INCREMENTAL WINS: {len(incremental_winners)}")
print(f"     BASIC-OPT WINS:   {len(basic_opt_winners)}")
print(f"     TIES:             {len(ties)}")

# Generate pie chart
counts = {
    'INCREMENTAL WINS': len(incremental_winners),
    'BASIC-OPT WINS':   len(basic_opt_winners),
    'TIE':              len(ties)
}

total = sum(counts.values())

labels = [
    f"INCREMENTAL Wins (>=2x)\n({counts['INCREMENTAL WINS']} formulas)",
    f"BASIC-OPT Wins (>=2x)\n({counts['BASIC-OPT WINS']} formulas)",
    f"Tie / Speedup < 2x\n({counts['TIE']} formulas)"
]

values  = [counts['INCREMENTAL WINS'], counts['BASIC-OPT WINS'], counts['TIE']]
colors  = ['#fe7c8a', '#85aae4', '#c1de6e']
explode = (0.05, 0.05, 0)

plt.figure(figsize=(8, 6))
plt.pie(
    values,
    labels=labels,
    autopct='%1.1f%%',
    startangle=140,
    colors=colors,
    explode=explode,
    textprops={'fontsize': 11}
)

plt.title(
    f'Algorithm Performance Distribution (Total: {total} formulas)',
    fontsize=14, fontweight='bold', pad=20
)
plt.tight_layout()

output_img = os.path.join(graphs_dir, 'performance_distribution.png')
plt.savefig(output_img, dpi=300)
print(f"[OK] Chart saved at: '{output_img}'")
plt.show()