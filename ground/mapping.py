from typing import Tuple
from enum import Enum

from aerpawlib.util import Coordinate, VectorNED

from util import *

class WorldMap:
    """
    keeps track of free space that can be traversed and does pathfinding as needed

    _map:
        n_d dict from a coordinate to an enum declaring traversability
    
    NOTE: the blocks occupied by terrain should be filled in by some algorithm elsewhere
          this likely will make use of fill_map at various altitudes
          TODO maybe add a function to download/load in a heightmap?
    """

    def __init__(self, center_coords: Coordinate, resolution: float):
        """
        center_coords defines the coordinate that is at (0,0,0) in our block system

        resolution defines the size of a block, in meters
        """
        self._map = {}
        self._center_coords = center_coords
        self._resolution = resolution
        self._drone_locations = {} # maps id -> position (Coordinate)

    def coord_to_block(self, coord: Coordinate) -> MapBlockCoord:
        delta_vec = coord - self._center_coords
        x, y, z = [int(i // self._resolution) for i in [delta_vec.east, delta_vec.north, -delta_vec.down]]
        return (x, y, z)

    def block_to_coord(self, block: MapBlockCoord) -> Coordinate:
        """
        returns the coordinate representing the corner of the block
        """
        x, y, z = [i*self._resolution for i in block]
        delta_vec = VectorNED(y, x, -z)
        return self._center_coords + delta_vec

    def fill_map(self, a: MapBlockCoord, b: MapBlockCoord, traversable: Traversability):
        """
        fill an area in this map ranging from a -> b with a specific traversability
        """
        for x in range(a[0], b[0]+1):
            for y in range(a[1], b[1]+1):
                for z in range(a[2], b[2]+1):
                    self._map[x, y, z] = traversable

    def update_drone(self, id: str, coordinate: Coordinate):
        self._drone_locations[id] = coordinate

    def drone_adjacent_blocks(self):
        """
        get dict mapping each drone's position to all blocks adjacent to that drone
        """
        adjs = {}
        for id in self._drone_locations:
            pos = self._drone_locations[id]
            drone_block = self.coord_to_block(pos)
            adjs[id] = adjacent_blocks(drone_block).keys() | {drone_block}
        return adjs

    def drone_block(self, drone_id: str) -> MapBlockCoord:
        """
        get block of a given drone
        """
        if drone_id not in self._drone_locations:
            return None
        return self.coord_to_block(self._drone_locations[drone_id])

    def find_path(self, a: MapBlockCoord, b: MapBlockCoord, drones_ignoring: set[str]) -> list[MapBlockCoord]:
        """
        find an optimal path from block "a" to block "b" avoiding any obstacles/adjacent-to-drone blocks

        this implements a version of dijkstra's algorithm so that we can easily add higher speed blocks later
        
        returns [path] if possible, else None
        """
        dists = {a: 0}
        paths = {a: None}
        blocks_to_traverse = [a]

        drone_occupied = set()
        drone_adj = self.drone_adjacent_blocks()
        for id in drone_adj:
            blocks = drone_adj[id]
            if id in drones_ignoring: 
                continue
            drone_occupied |= blocks

        while len(blocks_to_traverse) > 0:
            # treat as priority queue for dijk
            blocks_to_traverse = sorted(blocks_to_traverse, key=lambda x: dists[x])

            block = blocks_to_traverse[0]
            adj_block_dist = adjacent_blocks(block)
            for adj in adj_block_dist:
                if adj not in self._map:
                    # undeclared space, considered illegal
                    continue
                if self._map[adj] != Traversability.FREE:
                    # unavailable block
                    continue
                if adj in drone_occupied:
                    continue
                
                d_metric = adj_block_dist[adj]
                dist = dists[block] + d_metric # TODO update when introducing speed!
                if adj in dists and dist < dists[adj]:
                    paths[adj] = block
                    dists[adj] = dist
                if adj not in dists:
                    paths[adj] = block
                    dists[adj] = dist
                    blocks_to_traverse.append(adj)

            blocks_to_traverse.pop(0)
        
        if b not in paths:
            # impossible to get to, rip
            return None

        path = []
        curr = b
        while curr != a:
            path = [curr] + path
            curr = paths[curr]
        return path


if __name__ == "__main__":
    # testing fun
    test_map = WorldMap(Coordinate(35.7274488, -78.6960209, 100), 10)
    test_map.fill_map((-50, -50, 0), (50, 50, 0), Traversability.FREE)
    test_map.fill_map((5, -50, 0), (5, 49, 0), Traversability.BLOCKED)
    test_map.update_drone("me", test_map.block_to_coord((5,50,0)))
    print(test_map.find_path((0, 0, 0), (15, 25, 0), {"me"}))
