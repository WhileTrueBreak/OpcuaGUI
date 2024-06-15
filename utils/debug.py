import time

from colorama import Fore, Back, Style

TIMING_MAX_F = 0
TIMING_MAX_N = 0

TIMING_LAYER = 0
TIMING_TREE_NEXT = " "

TIMING_TOTAL = [0]
TIMING_LAYER_COUNT = [0]
TIMING_TREE = []

PROFILER_LAYER = 0
PROFILER_TOTAL = [0]
PROFILER_LAYER_COUNT = [0]
PROFILER_ACCUM = {}

def timing(func):
    def wrapper(*arg, **kw):
        global TIMING_MAX_F, TIMING_MAX_N, TIMING_LAYER, TIMING_TREE_NEXT
        TIMING_LAYER += 1
        TIMING_TOTAL.append(0)
        TIMING_LAYER_COUNT.append(0)
        TIMING_TREE.append(TIMING_TREE_NEXT)
        TIMING_TREE_NEXT = " "

        start = time.time_ns()

        out = func(*arg, **kw)

        end = time.time_ns()
        dt = (end-start)/1000
        TIMING_TOTAL[TIMING_LAYER-1] += dt
        TIMING_LAYER_COUNT[TIMING_LAYER-1] += 1
        tracked = TIMING_TOTAL.pop()
        TIMING_LAYER_COUNT.pop()
        TIMING_TREE.pop()
        fl = len(func.__qualname__)+TIMING_LAYER
        tl = len(f'{round(dt)-round(tracked)}')
        TIMING_MAX_N = max(TIMING_MAX_N, tl)
        TIMING_MAX_F = max(fl, TIMING_MAX_F)
        tab = f'{Fore.CYAN}{"".join(TIMING_TREE)}{"├" if TIMING_LAYER_COUNT[-1] > 1 else "┌"}{Style.RESET_ALL}'
        TIMING_TREE_NEXT = "│"
        print(f"{tab}{func.__qualname__} time:{' '*(TIMING_MAX_F-fl)} {Fore.RED}{round(dt)-round(tracked)}µs{Style.RESET_ALL}{' '*(TIMING_MAX_N-tl)} {Fore.BLUE}+{round(tracked)}µs{Style.RESET_ALL}")
        TIMING_LAYER -= 1
        return out
    return wrapper

def funcProfiler(ftype=None):
    def decorator(func):
        def wrapper(*arg, **kw):
            # return func(*arg, **kw)
            global PROFILER_LAYER
            PROFILER_LAYER += 1
            PROFILER_TOTAL.append(0)
            PROFILER_LAYER_COUNT.append(0)
            start = time.time_ns()
            out = func(*arg, **kw)
            end = time.time_ns()
            dt = (end-start)/1000000000

            PROFILER_TOTAL[PROFILER_LAYER-1] += dt
            PROFILER_LAYER_COUNT[PROFILER_LAYER-1] += 1
            tracked = PROFILER_TOTAL.pop()
            PROFILER_LAYER_COUNT.pop()

            if ftype not in PROFILER_ACCUM:
                PROFILER_ACCUM[ftype] = dt-tracked
            else:
                PROFILER_ACCUM[ftype] += dt-tracked
            PROFILER_LAYER -= 1
            return out
        return wrapper
    return decorator

def funclog(string):
    TIMING_LAYER_COUNT[TIMING_LAYER] += 1
    tab = f'{Fore.CYAN}{"".join(TIMING_TREE)}{"├" if TIMING_LAYER_COUNT[-1] > 1 else "┌"}{Style.RESET_ALL}'
    print(f"{tab}{string}{Style.RESET_ALL}")

def profileReport():
    global PROFILER_ACCUM
    total = sum(PROFILER_ACCUM.values())
    kv = sorted(PROFILER_ACCUM.items(), key=lambda x: x[1], reverse=True)
    lkey = len(max([k for k, v in kv], key=len))
    print(f'Profile Report:')
    for k, v in kv:
        print(f'  {k}: {' '*(lkey-len(k))}{Fore.BLUE}{round(v/total*100, 2)}%{Style.RESET_ALL}')

