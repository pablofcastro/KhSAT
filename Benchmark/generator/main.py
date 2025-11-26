import sys
import random
import kh 

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

    else:
        print(f'error: incorrect number of arguments for {argv[0]}')
        print(f'  use: {argv[0]} -r <b> | <n> <m> [<i.j>+]')

