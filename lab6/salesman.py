from mpi4py import MPI
from mpi4py.futures import MPIPoolExecutor
import numpy as np
import sys
import copy
from math import pi, cos, sin, sqrt
from random import random

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

maxsize = float('inf')


def point(r):
    theta = random() * 2 * pi
    return cos(theta) * r, sin(theta) * r


# Function to find the minimum edge cost
# having an end at the vertex i


def firstMin(adj, i):
    N = adj.shape[0]
    min = maxsize
    for k in range(N):
        if adj[i][k] < min and i != k:
            min = adj[i][k]

    return min

# function to find the second minimum edge
# cost having an end at the vertex i


def secondMin(adj, i):
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

# function that takes as arguments:
# curr_bound -> lower bound of the root node
# curr_weight-> stores the weight of the path so far
# level-> current level while moving
# in the search space tree
# curr_path[] -> where the solution is being stored
# which would later be copied to final_path[]


def TSP_rec(args):

    adj, curr_bound, curr_weight, level, curr_path, visited, final_res = args
    N = adj.shape[0]
    final_path = None

    # base case is when we have reached level N
    # which means we have covered all the nodes once
    if level == N:

        # check if there is an edge from
        # last vertex in path back to the first vertex
        if adj[curr_path[level - 1]][curr_path[0]] != 0:

            # curr_res has the total weight
            # of the solution we got
            curr_res = curr_weight + adj[curr_path[level - 1]][curr_path[0]]
            if curr_res < final_res:
                return curr_path, curr_res
        return None, None

    # for any other level iterate for all vertices
    # to build the search space tree recursively
    for i in range(N):

        # Consider next vertex if it is not same
        # (diagonal entry in adjacency matrix and
        # not visited already)
        if (adj[curr_path[level-1]][i] != 0 and
                visited[i] == False):
            temp = curr_bound
            curr_weight += adj[curr_path[level - 1]][i]

            # different computation of curr_bound
            # for level 2 from the other levels
            if level == 1:
                curr_bound -= ((firstMin(adj, curr_path[level - 1]) +
                                firstMin(adj, i)) / 2)
            else:
                curr_bound -= ((secondMin(adj, curr_path[level - 1]) +
                                firstMin(adj, i)) / 2)

            # curr_bound + curr_weight is the actual lower bound
            # for the node that we have arrived on.
            # If current lower bound < final_res,
            # we need to explore the node further
            if curr_bound + curr_weight < final_res:
                curr_path[level] = i
                visited[i] = True

                # call TSPRec for the next level
                final_path_candidate, final_res_candidate = TSP_rec((adj, curr_bound, curr_weight,
                                                                     level + 1, curr_path, visited, final_res))
                if final_res_candidate is not None:
                    final_res = final_res_candidate
                    final_path = final_path_candidate

            # Else we have to prune the node by resetting
            # all changes to curr_weight and curr_bound
            curr_weight -= adj[curr_path[level - 1]][i]
            curr_bound = temp

            # Also reset the visited array
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
        initial_bound -= ((secondMin(adj,
                          path[i]) + firstMin(adj, path[i+1])) / 2)
    return initial_bound


def TSP_init(N, d, adj):

    # Calculate initial lower bound for the root node
    # using the formula 1/2 * (sum of first min +
    # second min) for all edges. Also initialize the
    # curr_path and visited array
    curr_bound = 0
    visited = [False] * N

    # Compute initial bound
    for i in range(N):
        curr_bound += (firstMin(adj, i) + secondMin(adj, i))

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

        results = executor.map(TSP_rec, args)

        min_res = maxsize
        min_path = None
        for path, res in results:
            if res < min_res:
                min_res = res
                min_path = path

        print(min_path, min_res)

    end = MPI.Wtime()

    print(end - start)
