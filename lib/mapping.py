from typing import Tuple
from enum import Enum

from aerpawlib.util import Coordinate, VectorNED

from lib.util import *

class MapBlockCoordSystem:
    def __init__(self, center_coords: Coordinate, resolution: float):
        self._center_coords = center_coords
        self._resolution = resolution

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

    def get_block_center(self, block: MapBlockCoord) -> Coordinate:
        x, y, z = [i*self._resolution for i in block]
        x, y, z = [i+(0.5 * self._resolution) for i in [x,y,z]]
        delta_vec = VectorNED(y, x, -z)
        return self._center_coords + delta_vec

class WorldMap(MapBlockCoordSystem):
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
        super().__init__(center_coords, resolution)
        self._map = {}
        self._drone_locations = {} # maps id -> position (Coordinate)
        self._occupied_blocks = {}

    def heightslice(self, a: MapBlockCoord):
        """
        gets a slice of all declared blocks at a certain x, y coord

        the z (alt) component of the coord passed in is ignored
        """
        r = []
        for block in self._map:
            if block[0] == a[0] and block[1] == a[1]:
                r.append(block)
        return sorted(r, key=lambda x: x[2])

    def fill_map(self, a: MapBlockCoord, b: MapBlockCoord, traversable: Traversability):
        """
        fill an area in this map ranging from a -> b with a specific traversability
        """
        for x in range(a[0], b[0]+1):
            for y in range(a[1], b[1]+1):
                for z in range(a[2], b[2]+1):
                    self._map[x, y, z] = traversable

    def update_drone(self, id: str, coordinate: Coordinate):
        """
        update a drone's internal position and unreserve blocks as needed
        """
        self._drone_locations[id] = coordinate

        block = self.coord_to_block(coordinate)
        if self._occupied_blocks.get(block, None) == id:
            self.unreserve_block(id, block)
    
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

    def can_reserve_block(self, drone_id: str, block: MapBlockCoord, skip_adj: bool=False) -> MapBlockCoord:
        """
        see if a drone can reserve a block
        
        the block must be empty, adjacent, non-reserved, and not adjacent to any reserved blocks for a drone to do so
        """
        # non-reserved
        if block in self._occupied_blocks:
            return False

        # empty/free
        if block not in self._map:
            return False
        if self._map[block] != Traversability.FREE:
            return False
        
        # adjacent to this drone
        if not skip_adj:
            drone_block = self.drone_block(drone_id)
            if drone_block == None:
                return False # invalid drone
            adjs = adjacent_blocks(drone_block).keys() | {drone_block}
            if block not in adjs:
                return False
        
        # free from drones/drone adjacencies
        drone_adjs = self.drone_adjacent_blocks()
        for id in drone_adjs:
            if id == drone_id:
                continue
            if block in drone_adjs[id]:
                return False

        # not adjacent to any already reserved
        reserved_adjs = set()
        for reserved_block in self._occupied_blocks:
            reserved_id = self._occupied_blocks[reserved_block]
            if reserved_id == drone_id:
                # technically a drone can't reserve a block if it has already reserved one, but the purpose of this
                # function is more so to test the possiblity of reservation
                continue
            if reserved_block == block:
                return False
        return True

    def reserve_block(self, drone_id: str, block: MapBlockCoord, skip_adj: bool=False) -> bool:
        """
        attempt to have a drone "reserve" a block as occupied
        returns bool based on success (and thus if the drone can move in)

        a drone must be adjacent to a block and not have any other reservations to do so
        """
        if not self.can_reserve_block(drone_id, block, skip_adj=skip_adj):
            return False

        for block in self._occupied_blocks:
            if self._occupied_blocks[block] == drone_id:
                return False

        self._occupied_blocks[block] = drone_id
        return True

    def unreserve_block(self, drone_id: str, block: MapBlockCoord) -> bool:
        if block not in self._occupied_blocks:
            return False
        if self._occupied_blocks[block] != drone_id:
            return False
        del self._occupied_blocks[block]
        return True

    def find_path(self, a: MapBlockCoord, b: MapBlockCoord, drones_ignoring):
        """
        find an optimal path from block "a" to block "b" avoiding any obstacles/adjacent-to-drone blocks

        this implements a version of dijkstra's algorithm so that we can easily add higher speed blocks later
        
        returns [path] if possible, else None

        TODO this should probably be d* and/or something with caching
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

        reserved = set()
        for block in self._occupied_blocks:
            if self._occupied_blocks[block] in drones_ignoring:
                continue
            reserved |= adjacent_blocks(block).keys() | {block}

        while len(blocks_to_traverse) > 0:
            # treat as priority queue for dijk
            # blocks_to_traverse = sorted(blocks_to_traverse, key=lambda x: dists[x]) # dijk
            blocks_to_traverse = sorted(blocks_to_traverse, key=lambda x: math.hypot(b[0]-x[0], b[1]-x[1], b[2]-x[2])) # a*

            block = blocks_to_traverse[0]
            adj_block_dist = adjacent_blocks(block)
            for adj in adj_block_dist:
                if adj not in self._map:
                    # undeclared space, considered illegal
                    continue
                if self._map[adj] != Traversability.FREE:
                    # unavailable block
                    continue
                if adj in drone_occupied or adj in reserved:
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
    
            if block == b:
                break
            blocks_to_traverse.pop(0)
        
        if b not in paths:
            # impossible to get to, rip
            return None

        path = []
        curr = b
        while curr != a:
            path = [curr] + path
            curr = paths[curr]
        return [a] + path


if __name__ == "__main__":
    # testing fun
    test_map = WorldMap(Coordinate(35.7274488, -78.6960209, 100), 10)
    test_map.fill_map((-50, -50, 0), (50, 50, 0), Traversability.FREE)
    test_map.fill_map((5, -50, 0), (5, 49, 0), Traversability.BLOCKED)
    test_map.update_drone("me", test_map.block_to_coord((5,50,0)))
    print(test_map.find_path((0, 0, 0), (15, 25, 0), {"me"}))
