#!/usr/bin/env python

import mpi4py

from mpi4py import MPI

import math

import sys

import numpy as np

comm = MPI.COMM_WORLD

size = comm.Get_size()

rank = comm.Get_rank()

a = int(sys.argv[1]) if len(sys.argv) > 1 else 100
p = int(sys.argv[2]) if len(sys.argv) > 2 else 10
T = int(sys.argv[3]) if len(sys.argv) > 3 else 10

h_shape = (a+1, a+1)
h_size = np.prod(h_shape)
item_size = MPI.DOUBLE.Get_size()

nbytes = h_size * item_size if rank == 0 else 0

h_win = MPI.Win.Allocate_shared(nbytes, item_size, comm=comm)
h_buf, alloc_item_size = h_win.Shared_query(0)
assert alloc_item_size == item_size

h_ary = np.ndarray(buffer=h_buf, dtype='d', shape=h_shape)


def next_h(h, x: int, y: int):
    h[x][y] = (p/T + h[x][y-1] + h[x-1][y] + h[x][y+1] + h[x+1][y])/4


def next_col(h, x: int):
    for y in range(1, a):
        if x != 1:
            comm.Recv(source=rank-1, tag=y)
        next_h(h, x, y)
        if rank + 1 != size:
            comm.Ibsend(y, dest=rank+1, tag=y+1)


def next_iter(h):
    col = rank+1
    while col < a:
        next_col(h, col)
        col += size


comm.Barrier()
