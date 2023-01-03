#!/usr/bin/env python3
from __future__ import annotations

from mpi4py import MPI

import sys

import numpy as np
import json
import copy

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

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, Star):
            return __o.M == self.M and __o.x == self.x and __o.z == self.z and __o.y == self.y

    def __add__(self, other):
        if self == other:
            self.a_x += other.a_x
            self.a_y += other.a_y
            self.a_z += other.a_z
        return self

    def distance(self, other: Star) -> float:
        return np.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)

    def update_acceleration(self, other: Star, update_other: bool = False):
        dist_3 = self.distance(other) ** 3
        if dist_3 != 0:
            a_x_diff = G * (other.x - self.x) / dist_3
            a_y_diff = G * (other.y - self.y) / dist_3
            a_z_diff = G * (other.z - self.z) / dist_3
            self.a_x += a_x_diff * other.M
            self.a_y += a_y_diff * other.M
            self.a_z += a_z_diff * other.M
            if update_other:
                other.a_z -= a_z_diff * self.M
                other.a_y -= a_y_diff * self.M
                other.a_x -= a_x_diff * self.M

    def update_acceleration_list(self, others: list[Star], update_other: bool = False):
        for star in others:
            self.update_acceleration(star, update_other=update_other)

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


stars_file = sys.argv[1] if len(sys.argv) > 1 else 'stars.json'
with open(stars_file, 'r') as file:
    stars_list = file.readlines()

N = len(stars_list)
iterations = int(np.floor(p/2))
buff_size = int(np.ceil(N/p))

slice_start = rank*buff_size
slice_end = np.min([N, (rank+1)*buff_size])
stars = list(map(Star, stars_list[slice_start:slice_end]))

buff = copy.deepcopy(stars)

for i in range(iterations+1):
    if p != 1 and i != 0:
        req = comm.irecv(source=(rank-1+p) % p, tag=i)
        buff = req.wait()
    for j, star in enumerate(stars):
        # print(f'{rank}: {i} {j}', file=sys.stderr)
        star.update_acceleration_list(buff, update_other=(
            i != 0 and not (p % 2 == 0 and i == iterations)))
    if p != 1 and i != iterations:
        comm.isend(buff, dest=(rank+1) % p, tag=i+1)

if p != 1:  # and iterations + 1 != p:
    # print(f'{rank}: dest={(rank-iterations+p) % p} source={(rank+iterations) % p}', file=sys.stderr)
    comm.isend(buff, dest=(rank-iterations+p) % p, tag=0)
    req = comm.irecv(source=(rank+iterations) % p, tag=0)
    buff = req.wait()
    stars = [s+b for s, b in zip(stars, buff)]

results = comm.gather(stars, root=0)
if rank == 0:
    for sublist in results:
        for item in sublist:
            print(json.dumps(item.__dict__))
