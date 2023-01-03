#!/usr/bin/env python3
from __future__ import annotations

from mpi4py import MPI

import sys

import numpy as np
import json

import matplotlib.pyplot as plt

comm = MPI.COMM_WORLD

p = comm.Get_size()

rank = comm.Get_rank()

G = 3


class Star:
    M = 0
    x = 0
    y = 0
    z = 0
    v_x = 0
    v_y = 0
    v_z = 0
    a_x = 0
    a_y = 0
    a_z = 0

    def __init__(self, s: str) -> None:
        self.reader(json.loads(s))
        self.a_x = 0
        self.a_y = 0
        self.a_z = 0

    def distance(self, other: Star) -> float:
        return np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)

    def update_acceleration(self, other: Star):
        dist_3 = self.distance(other) ** 3
        if dist_3 != 0:
            self.a_x += G * other.M * (other.x - self.x) / dist_3
            self.a_y += G * other.M * (other.y - self.y) / dist_3
            self.a_z += G * other.M * (other.z - self.z) / dist_3

    def update_acceleration_list(self, others: list[Star]):
        for star in others:
            self.update_acceleration(star)

    def reader(self, input_dict, *kwargs):
        for key in input_dict:
            try:
                setattr(self, key, input_dict[key])
            except:
                print(
                    f'no such attribute: {key}, please consider add it at init')
                continue

    def __str__(self) -> str:
        return f'{self.M} {self.x} {self.y} {self.z} {self.a_x:.4f} {self.a_y:.4f} {self.a_z:.4f}'


comm.Barrier()
start = MPI.Wtime()

stars_file = sys.argv[1] if len(sys.argv) > 1 else 'stars.json'
with open(stars_file, 'r') as file:
    stars_list = file.readlines()

N = len(stars_list)
buff_size = int(np.ceil(N/p))

stars = list(map(Star, stars_list[rank*buff_size:(rank+1)*buff_size]))

buff = stars

for i in range(p):
    if p != 1 and i != 0:
        req = comm.irecv(source=(rank-1+p) % p, tag=i)
        buff = req.wait()
    for j, star in enumerate(stars):
        # print(f'{rank}: {j}', file=sys.stderr)
        star.update_acceleration_list(buff)
    if p != 1:
        comm.isend(buff, dest=(rank+1) % p, tag=i+1)

results = comm.gather(stars, root=0)

comm.Barrier()
end = MPI.Wtime()

if rank == 0:
    # for sublist in results:
    #     for item in sublist:
    #         print(json.dumps(item.__dict__))
    print(f'ring,{p},{N},{end-start}')
