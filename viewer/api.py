import requests
import threading
import time

from raylib import *

from aerpawlib.util import Coordinate

from lib.mapping import *
from lib.util import *

from viewer.render import *

class MapHandler():
    def __init__(self, ground_host: str, skip_http=False):
        self._ground_host = ground_host
        
        if not skip_http:
            resp = requests.get(
                    url=f"http://{self._ground_host}/viewer/coordinates"
                    )
            assert resp.status_code == 200
            j = resp.json()
            self._world_map = WorldMap(deserialize_coordinate(j["center"]), j["resolution"])
        else:
            self._world_map = None
        self._welded_blocks = None

    def weld_map(self):
        m = self._world_map._map.copy()
        if len(m) == 0:
            self._welded_blocks = []
            return

        xs = {i[0] for i in m}
        ys = {i[1] for i in m}
        zs = {i[2] for i in m}

        x_bounds = (min(xs), max(xs))
        y_bounds = (min(ys), max(ys))
        z_bounds = (min(zs), max(zs))

        x_constrained_slices = [] # (corner1, corner2)
        slices_building = {} # (y, z): corner1

        for x in range(x_bounds[0], x_bounds[1]+1):
            for y in range(y_bounds[0], y_bounds[1]+1):
                for z in range(z_bounds[0], z_bounds[1]+1):
                    if (y, z) in slices_building:
                        if (x, y, z) not in m \
                                or m[(x, y, z)] != Traversability.BLOCKED:
                            x_constrained_slices.append((slices_building[(y, z)], (x, y, z)))
                            del(slices_building[(y, z)])
                    elif (x, y, z) in m \
                            and m[(x, y, z)] == Traversability.BLOCKED:
                        slices_building[(y, z)] = (x, y, z)
        for slice in slices_building:
            y, z = slice
            x_constrained_slices.append((slices_building[slice], (x_bounds[1], y, z)))

        # just 1d for now.
        # compute sizes
        blocks = []
        for slice in x_constrained_slices:
            x1, y1, z1 = slice[0]
            x2, y2, z2 = slice[1]
            dx = x2-x1
            dy = y2-y1 + 1
            dz = z2-z1 + 1
            blocks.append(((x1-1, y1-1, z1-1), (dx, dy, dz)))

        self._welded_blocks = blocks

    def render_map(self, camera):
        if self._welded_blocks == None:
            self.weld_map()
        # m = self._world_map._map.copy()
        o = self._world_map._occupied_blocks.copy()
        # for coord in m:
        #     if m[coord] == Traversability.BLOCKED:
        #         draw_cube(camera, coord, RED, self._world_map)
        for block in self._welded_blocks:
            draw_rect(camera, block[0], block[1], RED)

        for drone_block in o:
            draw_cube(camera, drone_block, BLUE, self._world_map, o[drone_block])

    def update_map(self):
        resp = requests.get(
                url=f"http://{self._ground_host}/viewer/map"
                )
        assert resp.status_code == 200
        j = resp.json()
        # TODO better serialization
        n_map = {}
        for block in j["blocks"]:
            n_map[deserialize_block(block["block"])] = Traversability(block["val"])
        n_occupied = {}
        for block in j["occupied"]:
            n_occupied[deserialize_block(block["block"])] = block["val"]
        if n_map != self._world_map._map:
            self._world_map._map = n_map
            self._welded_blocks = None
        self._world_map._occupied_blocks = n_occupied

    def get_daemon_func(self, stop_event: threading.Event, update_delay: int=1):
        def _inner():
            while not stop_event.is_set():
                self.update_map()
                time.sleep(update_delay)
        return _inner

if __name__ == "__main__":
    world_map = WorldMap(Coordinate(35.7274488, -78.6960209, 30), 10)
    
    # world_map.fill_map((-20, -20, -2), (20, 20, 2), Traversability.FREE)
    # world_map.fill_map((-20, -1, -3), (20, 1, -1), Traversability.BLOCKED)
    
    world_map.fill_map((-20, -20, -2), (20, 20, 2), Traversability.FREE)
    world_map.fill_map((-20, 0, -2), (20, 10, 2), Traversability.BLOCKED)
    world_map.fill_map((-3, 0, -1), (3, 10, 1), Traversability.FREE)

    h = MapHandler("", True)
    h._world_map = world_map
    h.weld_map()
