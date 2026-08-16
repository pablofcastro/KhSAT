import sys
import random
import s5

benchmark_size = 20
benchmark_instance = 0
benchmark_path = "../formulasS5/"

if __name__ == '__main__':

    argv = sys.argv[1:]

    if len(argv) >= 2:
        if argv[0] == "-r":
            # in this case we generate a random formula with the given parameters

            n = int(argv[1])
            m = int(argv[2])
            l = int(argv[3])
            p = float(argv[4])

            for i in range(2,benchmark_size) :
                for j in range(10) :
                    fname = benchmark_path+f"formula{i}-{n}-{m}-{l}-{p}.s5"
                    print("Generating formula: "+fname)
                    ffile = open(fname,'w')
                    ffile.write(f"{s5.phi(n, m, l, p)}")
                    ffile.close()

    elif len(argv) == 1 and argv[0] == "-benchmark" :
        l = 3
        p = 0.5
        # in this case, we generate the benchmark based on the relationship between clauses and the number of variables
        
        n_values = [100,120]
        pd_values = [0.2, 0.45,0.5,0.55, 0.8]
        for i in range(2,benchmark_size) :
            for n in n_values:                
                for pd in pd_values:
                    ratios = [2.0, 4.0, 5.0, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 11.0, 12.0, 15.0]
                    
                    for j in ratios:
                        m = int(n * j) 
                        fname = benchmark_path + f"formula{i}-{n}-{m}-{l}-{p}-{pd}.s5"
                        print(f"Generating: {fname} | Ratio: {j}")
                        with open(fname, 'w') as ffile:
                            ffile.write(f"{s5.phi(n, m, l, p, pd)}")
    else:
        print(f'error: incorrect number of arguments.')
        print(f'  use: {argv[0]} | -benchmark')

