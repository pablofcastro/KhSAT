import sys
import random
import kh 

benchmark_size = 50
benchmark_instance = 0
benchmark_path = "../formulas/"

if __name__ == '__main__':

    argv = sys.argv[1:]

    if len(argv) >= 2:


        if argv[0] == "-r":

            b = int(argv[1])

            argv  = [f"{random.randint(0,b)}"]
            argv += [f"{random.randint(0,b)}"]

            for i in range(random.randint(0,b)):

                argv += [f"{random.randint(0,b)}.{random.randint(0,b)}"]

        fname = "f."+".".join(argv) + ".kh"
          
        ffile = open(fname,'w')

        n = int(argv[0])
        m = int(argv[1])

        s = [tuple(map(int, s.split("."))) for s in argv[2:]]

        ffile.write(f"{kh.phi(n,m,s)}")
        
        ffile.close()
    elif len(argv) == 1 and argv[0] == "-benchmark" :
        # in this case we generate the benchmark
        for i in range(2,benchmark_size) :
            for j in range(10) :
                n = random.randint(0,i)
                m = i - n
                #s = [(random.randint(0,b//2), random.randint(0,b//2)) for b in range(random.randint(0,i))]
                fname = benchmark_path+f"formula{i}-{n}-{m}.kh"
                print("Generating formula: "+fname)
                ffile = open(fname,'w')
                ffile.write(f"{kh.phi(n, m, i)}")
                ffile.close()
    else:
        print(f'error: incorrect number of arguments.')
        print(f'  use: {argv[0]} -r <b> | <n> <m> [<i.j>+] | -benchmark')

