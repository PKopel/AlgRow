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

h_win = MPI.Win.Allocate_shared(nbytes, item_size, comm=comm)
h_buf, alloc_item_size = h_win.Shared_query(0)
assert alloc_item_size == item_size

h_ary = np.ndarray(buffer=h_buf, dtype='d', shape=h_shape)
if rank == 0:
    h_ary.fill(0)


def next_h(h, x: int, y: int):
    h[x][y] = (p/T + h[x][y-1] + h[x-1][y] + h[x][y+1] + h[x+1][y])/4


def next_col(h, x: int):
    for y in range(1, a-1):
        if x != 1:
            source = (size+rank-1) % size
            comm.Recv(np.zeros(1), source=source, tag=y)
        next_h(h, x, y)
        if x + 1 != a:
            dest = (rank+1) % size
            comm.Isend(np.zeros(1), dest=dest, tag=y)


def next_iter(h):
    col = rank+1
    while col < a-1:
        next_col(h, col)
        col += size


comm.Barrier()
start = MPI.Wtime()

for i in range(1000):
    next_iter(h_ary)
    comm.Barrier()
    
end = MPI.Wtime()

if rank == 0:
    scale = 400//a
    upscale = np.ones((scale, scale))
    plt.imsave(f'./result.png', np.kron(h_ary, upscale), cmap='hot')
    np.savetxt("result.csv", h_ary, delimiter=",", fmt='%10.5f')
    print(f'{a},{p},{T},{end-start}')
