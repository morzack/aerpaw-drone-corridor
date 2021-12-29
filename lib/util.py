import math
from typing import Tuple
from enum import Enum

from aerpawlib.util import Coordinate

MapBlockCoord = Tuple[int, int, int]    # coord in x, y, z measuring blocks away from central block
                                        # note that +x = east, +y = north, +z = up

class Traversability(Enum):
    FREE = 1
    ADJ_BLOCKED = 2
    BLOCKED = 3


def adjacent_blocks(m: MapBlockCoord):
    """
    returns dict where keys are positions and values are distances (1 or sqrt(2))
    """
    r = {}
    x, y, z = m
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                if dx == dy == dz == 0:
                    continue
                r[x+dx, y+dy, z+dz] = math.hypot(dx, dy, dz)
    return r

def serialize_coordinate(c: Coordinate):
    return {
            "lat": c.lat,
            "lon": c.lon,
            "alt": c.alt,
            }

def deserialize_coordinate(x) -> Coordinate:
    return Coordinate(x["lat"], x["lon"], x["alt"])

def serialize_block(b: MapBlockCoord):
    return {
            "x": b[0],
            "y": b[1],
            "z": b[2],
            }

def deserialize_block(x) -> MapBlockCoord:
    return (x["x"], x["y"], x["z"])
