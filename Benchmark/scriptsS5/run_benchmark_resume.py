import subprocess
import os
import sys
import csv
import argparse
import re
import statistics
import concurrent.futures

# Importamos las librerías necesarias para parsear S5 y contar los mundos rápidamente
import S5.parser_s5 as s5parser
import S5.NNFVisitor as tonnf
import S5.DiamondVisitor as diamond_counter

# Aumentamos el límite de recursión por las dudas para el parseo inicial
sys.setrecursionlimit(10000)

def count_worlds(file_path):
    """Parsea rápidamente la fórmula y cuenta los mundos posibles (Diamantes + 1)."""
    try:
        with open(file_path, 'r') as f:
            formula_str = f.read()
        parsed = s5parser.parse(formula_str)
        nnf_form = parsed.accept(tonnf.ToNNF())
        mundos = nnf_form.accept(diamond_counter.DiamondVisitor()) + 1
        return mundos
    except Exception as e:
        print(f"Error contando mundos en {file_path}: {e}")
        return -1 # Retorna -1 si hay un error en el parseo

def process_single_file(file, runs):
    """Procesa una sola fórmula y retorna un diccionario con los resultados."""
    row = {}
    instance = file.replace(".s5","").split('-')
    row["form"] = instance[0]
    row["n"] = instance[1]
    row["m"] = instance[2]
    row["ratio"] = round(int(instance[2])/int(instance[1]), 2)
    row["p"] = instance[4]
    row["pd"] = instance[5]
    
    instance_path = os.path.join("../formulasS5/", file)
    
    # NUEVO: Contamos los mundos antes de pasárselo a Z3
    row["worlds"] = count_worlds(instance_path)
    
    times = []
    results = []
    timed_out = False
    
    for r in range(runs) :
        try :
            # Ejecutamos el solver (asegúrate de que tu s5_solver.py tenga el sys.setrecursionlimit(10000))
            output = subprocess.run([sys.executable, "../../s5_solver.py", "-f", instance_path], timeout=900, capture_output=True).stdout.decode()
            lines = output.splitlines()
            for line in lines :
                if "Time:" in line :
                    times.append(float(line.split()[1]))
                elif "SAT" in line or "UNSAT" in line or "unsat" in line :
                    results.append("SAT" if "SAT" in line else "UNSAT")
        except subprocess.TimeoutExpired:
             print(f"Timeout en la corrida {r+1} de {file}")
             timed_out = True
        except Exception as e:
            print(f'Error ejecutando {file}: {e}')
            timed_out = True
            
    row["time"] = str(statistics.median(times)) if times else "900"
    row["result"] = results[0] if results else ("TO" if timed_out else "TO")
    row["size"] = os.path.getsize(instance_path)
    
    return row

def process_batch(batch_num, runs) :
    pattern = re.compile(r"formula(\d+)-(\d+)-(\d+)-(\d+)-([\d.]+)-([\d.]+).s5$")
    files_to_process = []
    
    csv_filename = f"output-batch{batch_num}.csv"
    
    # 1. LEER LO QUE YA ESTÁ HECHO (Lógica de Reanudación)
    processed_formulas = set() # Usamos un Set para búsquedas O(1)
    
    # Si el archivo CSV ya existe, leemos qué fórmulas ya tienen resultados
    if os.path.exists(csv_filename):
        with open(csv_filename, 'r', newline='') as f:
            reader = csv.reader(f)
            # Nos saltamos el encabezado si existe
            next(reader, None) 
            for row in reader:
                 # Verificamos que la fila no esté vacía antes de intentar acceder
                 if row: 
                     # Reconstruimos el nombre del archivo basándonos en las columnas
                     # Las columnas en el CSV actual son: form, n, m, ratio, p, worlds, time, result, size
                     # Asumiendo l=3. (Si usas otro 'l', tendrás que leerlo del nombre original de alguna forma)
                     # Para evitar problemas con reconstruir el nombre, es mejor comparar 'form' + 'n' + 'm'
                     form_id = row[0]
                     n_val = row[1]
                     m_val = row[2]
                     # Creamos un identificador único para la fórmula
                     formula_key = f"{form_id}-{n_val}-{m_val}"
                     processed_formulas.add(formula_key)
        print(f"Encontradas {len(processed_formulas)} fórmulas ya procesadas en {csv_filename}. Se omitirán.")

    # 2. SELECCIONAR QUÉ FALTA PROCESAR
    for filename in os.listdir("../formulasS5/"):
        m = pattern.match(filename)
        if m:
            inst_id = int(m.group(1))
            if inst_id < batch_num*10 and inst_id >= (batch_num-1)*10 :
                
                # Extraer info para comprobar si ya se hizo
                parts = filename.replace(".s5","").split('-')
                formula_key = f"{parts[0]}-{parts[1]}-{parts[2]}"
                
                # Si la fórmula NO está en el conjunto de procesadas, la agregamos a la lista
                if formula_key not in processed_formulas:
                     files_to_process.append(filename)
                
    total_files_batch = len(files_to_process)
    if total_files_batch == 0:
        print(f"El Batch {batch_num} ya está 100% completo. No hay nada que procesar.")
        return

    cores = os.cpu_count()
    print(f"Batch {batch_num}: Procesando {total_files_batch} fórmulas faltantes en PARALELO usando {cores} núcleos...")
    
    # Definimos los nombres de las columnas explícitamente, incluyendo "worlds"
    fieldnames = ["form", "n", "m", "ratio", "p", "pd", "worlds", "boxes", "diamonds", "modal_ratio", "time", "result", "size"]
    
    # 3. ESCRIBIR EN EL CSV INMEDIATAMENTE DESPUÉS DE CADA RESULTADO
    # Abrimos el archivo en modo "append" ('a'). Si no existe, se crea.
    # Si la lista de procesados está vacía, escribimos el encabezado.
    write_header = not os.path.exists(csv_filename) or os.path.getsize(csv_filename) == 0

    with open(csv_filename, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
            
        processed_count = 0
        
        # Ejecución paralela
        with concurrent.futures.ProcessPoolExecutor(max_workers=cores) as executor:
            # Enviamos los trabajos
            futures = {executor.submit(process_single_file, f, runs): f for f in files_to_process}
            
            # A medida que terminan...
            for future in concurrent.futures.as_completed(futures):
                try:
                    row_data = future.result()
                    # ¡MAGIA!: Escribimos el resultado directamente en el disco
                    writer.writerow(row_data)
                    # Forzamos a Python a guardar en el disco (flush) por si cancelas con Ctrl+C
                    csvfile.flush() 
                    
                except Exception as exc:
                    print(f"Una fórmula generó una excepción: {exc}")
                    
                processed_count += 1
                if processed_count % 10 == 0 or processed_count == total_files_batch:
                    print(f"Progreso Batch {batch_num}: {round((processed_count/total_files_batch) * 100, 1)}% ({processed_count}/{total_files_batch})")

if __name__ == "__main__" :
    parser = argparse.ArgumentParser(description="Process the formulas in batches.")

    parser.add_argument(
        "--batch",
        type=int,
        default=10,
        help="The batch to be processed: 1,2,3,4,5"
    )

    parser.add_argument(
        "--all",
        type=bool,
        default=None,
        help="Option to process all the batches"
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Number of solver executions per formula to compute the median time"
    )
    args = parser.parse_args()
    
    if not args.all :
        print(f"Procesando batch: {args.batch}")
        process_batch(args.batch, args.runs)
        print(f"Resultado guardado en output-batch{args.batch}.csv")
    else :
        for i in [1,2,3,4,5] :
            print(f"--- Iniciando Batch {i} ---")
            process_batch(i, args.runs)