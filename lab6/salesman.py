from mpi4py import MPI
from mpi4py.futures import MPIPoolExecutor
import numpy as np
import sys
import copy
from math import pi, cos, sin, sqrt
from random import random

comm = MPI.COMM_WORLD
size = comm.Get_size()
rank = comm.Get_rank()

maxsize = float('inf')


def point(r):
    theta = random() * 2 * pi
    return cos(theta) * r, sin(theta) * r


def first_min(adj, i):
    N = adj.shape[0]
    min = maxsize
    for k in range(N):
        if adj[i][k] < min and i != k:
            min = adj[i][k]

    return min


def second_min(adj, i):
    N = adj.shape[0]
    first, second = maxsize, maxsize
    for j in range(N):
        if i == j:
            continue
        if adj[i][j] <= first:
            second = first
            first = adj[i][j]

        elif (adj[i][j] <= second and
                adj[i][j] != first):
            second = adj[i][j]

    return second


def TSP_rec(args):

    adj, curr_bound, curr_weight, level, curr_path, visited, final_res = args
    N = adj.shape[0]
    final_path = None

    if level == N:

        if adj[curr_path[level - 1]][curr_path[0]] != 0:

            curr_res = curr_weight + adj[curr_path[level - 1]][curr_path[0]]
            if curr_res < final_res:
                return curr_path, curr_res
        return None, None

    for i in range(N):

        if (adj[curr_path[level-1]][i] != 0 and
                visited[i] == False):
            temp = curr_bound
            curr_weight += adj[curr_path[level - 1]][i]
            curr_bound -= ((second_min(adj, curr_path[level - 1]) +
                            first_min(adj, i)) / 2)

            if curr_bound + curr_weight < final_res:
                curr_path[level] = i
                visited[i] = True

                final_path_candidate, final_res_candidate = TSP_rec((adj, curr_bound, curr_weight,
                                                                     level + 1, curr_path, visited, final_res))
                if final_res_candidate is not None:
                    final_res = final_res_candidate
                    final_path = final_path_candidate

            curr_weight -= adj[curr_path[level - 1]][i]
            curr_bound = temp

            visited = [False] * len(visited)
            for j in range(level):
                if curr_path[j] != -1:
                    visited[curr_path[j]] = True

    return final_path, final_res


def generate_paths(N, current, visited, max_depth):
    if max_depth == 1:
        return [(current, copy.deepcopy(visited))]
    paths = []
    for i in range(N):
        if not visited[i]:
            visited[i] = True
            paths += (generate_paths(N, current + [i], visited, max_depth-1))
            visited[i] = False

    return paths


def path_weigth(adj, path):
    weigth = 0
    for i in range(len(path)-1):
        weigth += adj[path[i]][path[i+1]]
    return weigth


def path_bound(adj, path, initial_bound):
    for i in range(len(path)-1):
        initial_bound -= ((second_min(adj,
                          path[i]) + first_min(adj, path[i+1])) / 2)
    return initial_bound


def TSP_init(N, d, adj):
    curr_bound = 0
    visited = [False] * N

    # Compute initial bound
    for i in range(N):
        curr_bound += (first_min(adj, i) + second_min(adj, i))

    # Compute initial paths
    visited[0] = True
    init_paths = generate_paths(N, [0], visited, d)

    args_list = []
    for path, visit in init_paths:
        curr_path = path + [-1] * (N - d)
        pw = path_weigth(adj, path)
        pb = path_bound(adj, path, curr_bound)
        args_list.append((adj, pb, pw, d, curr_path, visit, maxsize))

    return args_list


if __name__ == '__main__':

    start = MPI.Wtime()

    N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    with MPIPoolExecutor() as executor:
        nodes = [point(10) for _ in range(N)]
        print(nodes)

        adj = np.zeros((N, N))

        for i in range(N):
            for j in range(N):
                if i != j:
                    x1, y1 = nodes[i]
                    x2, y2 = nodes[j]
                    adj[i, j] = sqrt((x1-x2)**2+(y1-y2)**2)

        args = TSP_init(N, d, adj)

        print(f'init done, {len(args)}')

        results = executor.map(TSP_rec, args)

        min_res = maxsize
        min_path = None
        for path, res in results:
            if res < min_res:
                min_res = res
                min_path = path

        print(min_path, min_res)

    end = MPI.Wtime()

    print(f'{N},{d},{size},{end - start}')
