import time

from colorama import Fore, Back, Style

MAX_F = 0
MAX_N = 0
LAYER = 0
TREE_NEXT = " "

total = [0]
lCount = [0]
tree = []

def timing(func):
    def wrapper(*arg, **kw):
        global MAX_F, MAX_N, LAYER, TREE_NEXT
        LAYER += 1
        total.append(0)
        lCount.append(0)
        tree.append(TREE_NEXT)
        TREE_NEXT = " "
        start = time.time_ns()

        out = func(*arg, **kw)

        end = time.time_ns()
        dt = (end-start)/1000
        total[LAYER-1] += dt
        lCount[LAYER-1] += 1
        tracked = total.pop()
        lCount.pop()
        tree.pop()
        fl = len(func.__qualname__)+LAYER
        tl = len(f'{round(dt)}')
        MAX_N = max(MAX_N, tl)
        MAX_F = max(fl, MAX_F)
        tab = f'{Fore.CYAN}{"".join(tree)}{"├" if lCount[-1] > 1 else "┌"}{Style.RESET_ALL}'
        TREE_NEXT = "│"
        print(f"{tab}{func.__qualname__} time:{' '*(MAX_F-fl)} {Fore.RED}{round(dt)}µs{Style.RESET_ALL}{' '*(MAX_N-tl)} {Fore.BLUE}-{round(tracked)}µs{Style.RESET_ALL}")
        LAYER -= 1
        return out
    return wrapper

def funclog(string):
    lCount[LAYER] += 1
    tab = f'{Fore.CYAN}{"".join(tree)}{"├" if lCount[-1] > 1 else "┌"}{Style.RESET_ALL}'
    print(f"{tab}{string}{Style.RESET_ALL}")