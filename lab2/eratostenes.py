#!/usr/bin/env python

import mpi4py

from mpi4py import MPI

import math

import sys

import numpy as np

comm = MPI.COMM_WORLD

size = comm.Get_size()

rank = comm.Get_rank()

comm.Barrier()

n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
sqrtn = math.floor(math.sqrt(n))

# A = range(2, n+1)
B = range(2, sqrtn+1)
C = range(sqrtn+1, n+1)

sliceSize = (n - sqrtn) // size
sliceStart = rank * sliceSize
sliceEnd = (rank+1) * sliceSize

CSlice = C[sliceStart:sliceEnd]

BPrimes = B
i = 0
while i < len(BPrimes):
    x = BPrimes[i]
    BPrimes = [y for y in BPrimes if y == x or y % x != 0]
    i += 1

for x in BPrimes:
    CSlice = [y for y in CSlice if y % x != 0]

sendBuf = np.array(CSlice)
recvBuf = np.zeros([size, sliceSize], dtype=np.dtype(int)
                   ) if rank == 0 else None

comm.Gather(sendBuf, recvBuf, root=0)

if rank == 0:
    results = recvBuf.flatten()
    results = results[np.nonzero(results)]
    print(results.tolist())
