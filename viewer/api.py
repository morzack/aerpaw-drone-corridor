import requests
import threading
import time

from raylib import *

from lib.mapping import *
from lib.util import *

from viewer.render import *

class MapHandler():
    def __init__(self, ground_host: str):
        self._ground_host = ground_host
        
        resp = requests.get(
                url=f"http://{self._ground_host}/viewer/coordinates"
                )
        assert resp.status_code == 200
        j = resp.json()
        self._world_map = WorldMap(deserialize_coordinate(j["center"]), j["resolution"])

    def render_map(self, camera):
        m = self._world_map._map.copy()
        o = self._world_map._occupied_blocks.copy()
        for coord in m:
            if m[coord] == Traversability.BLOCKED:
                draw_cube(camera, coord, RED, self._world_map)

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
        self._world_map._map = n_map
        self._world_map._occupied_blocks = n_occupied

    def get_daemon_func(self, stop_event: threading.Event, update_delay: int=1):
        def _inner():
            while not stop_event.is_set():
                self.update_map()
                time.sleep(update_delay)
        return _inner
