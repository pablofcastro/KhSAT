import sys
import random
import s5

benchmark_size = 50
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
        for i in range(2,benchmark_size) :
            for j in range(10) :
                # n = random.randint(1,i)
                n = 15
                m = int(n*j) # 4,3 is the threshold for 3-SAT problems, we can use it as a reference for S5 problems
                fname = benchmark_path+f"formula{i}-{n}-{m}-{l}-{p}.s5"
                print("Generating formula: "+fname)
                ffile = open(fname,'w')
                ffile.write(f"{s5.phi(n, m, l, p)}")
                ffile.close()
    else:
        print(f'error: incorrect number of arguments.')
        print(f'  use: {argv[0]} | -benchmark')

