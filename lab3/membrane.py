#!/usr/bin/env python3

from mpi4py import MPI

import sys

import numpy as np

import matplotlib.pyplot as plt

comm = MPI.COMM_WORLD

size = comm.Get_size()

rank = comm.Get_rank()

a = int(sys.argv[1]) if len(sys.argv) > 1 else 100
p = int(sys.argv[2]) if len(sys.argv) > 2 else 10
T = int(sys.argv[3]) if len(sys.argv) > 3 else 10

h_shape = (a, a)
h_size = np.prod(h_shape)
item_size = MPI.DOUBLE.Get_size()

nbytes = h_size * item_size if rank == 0 else 0


def next_h(h, x: int, y: int):
    h[x][y] = (p/T + h[x][y-1] + h[x-1][y] + h[x][y+1] + h[x+1][y])/4

# wavefront


# def wavefront(h, x: int):
#     for y in range(1, a-1):
#         if x != 1:
#             source = (size+rank-1) % size
#             comm.Recv(np.zeros(1), source=source, tag=y)
#         next_h(h, x, y)
#         if x + 1 != a:
#             dest = (rank+1) % size
#             comm.Isend(np.zeros(1), dest=dest, tag=y)


# def next_iter_wavefront(h):
#     col = rank+1
#     while col < a-1:
#         wavefront(h, col)
#         col += size


# coloring
def coloring(h, x: int, odd: bool):
    start = 1 + (x % 2) if odd else 2 - (x % 2)
    for y in range(start, a-1, 2):
        next_h(h, x, y)


def next_iter_coloring(h):
    col = rank+1
    while col < a-1:
        coloring(h, col, True)
        col += size
    comm.Barrier()
    col = rank+1
    while col < a-1:
        coloring(h, col, False)
        col += size


comm.Barrier()
start = MPI.Wtime()

h_win = MPI.Win.Allocate_shared(nbytes, item_size, comm=comm)
h_buf, alloc_item_size = h_win.Shared_query(0)

h_ary = np.ndarray(buffer=h_buf, dtype='d', shape=h_shape)
h_ary.fill(0)

for i in range(1000):
    next_iter_coloring(h_ary)

comm.Barrier()
end = MPI.Wtime()

if rank == 0:
    # scale = 400//a
    # upscale = np.ones((scale, scale))
    # plt.imsave(f'./result.png', np.kron(h_ary, upscale), cmap='hot')
    # np.savetxt("result.csv", h_ary, delimiter=",", fmt='%10.5f')
    print(f'{a},{p},{T},{size},{end-start}')
