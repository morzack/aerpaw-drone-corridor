import threading
import time

import dronekit

from aerpawlib.util import Coordinate

from lib.mapping import WorldMap
from lib.util import *

from ground.ground_logger import Logger


class DroneConnection:
    def __init__(self, id: str, conn_str: str, world_map: WorldMap):
        self._id = id
        self._conn_str = conn_str
        self._world_map = world_map
        
        self._vehicle = dronekit.connect(self._conn_str, wait_ready=False)

        self._has_heartbeat = False

        def _heartbeat_listener(_, __, val):
            if val > 1 and self._has_heartbeat:
                self._has_heartbeat = False
            elif val < 1 and not self._has_heartbeat:
                self._has_heartbeat = True
        self._vehicle.add_attribute_listener("last_heartbeat", _heartbeat_listener)

    def vehicle_heartbeat_ok(self):
        return self._has_heartbeat

    def location(self) -> Coordinate:
        loc = self._vehicle.location.global_relative_frame
        if loc.lat == None or loc.lon == None or loc.alt == None:
            return None
        return Coordinate(loc.lat, loc.lon, loc.alt)

    def block(self) -> MapBlockCoord:
        if self.location() == None:
            return None
        return self._world_map.coord_to_block(self.location())


class DroneListing:
    def __init__(self, world_map: WorldMap, logger: Logger):
        self._world_map = world_map
        self._drones = {}
        self._logger = logger
    
    def add_drone(self, id: str, conn_str: str):
        new_drone = DroneConnection(id, conn_str, self._world_map)
        self._drones[id] = new_drone

    def update_map(self):
        for drone in self._drones.values():
            if drone.vehicle_heartbeat_ok() and drone.location() != None and drone.block() != None:
                self._world_map.update_drone(drone._id, drone.location())
                self._logger.update_drone(drone._id, drone.block())
    
    def get_daemon_func(self, stop_event: threading.Event, update_delay: int=1):
        def _inner():
            while not stop_event.is_set():
                self.update_map()
                time.sleep(update_delay)
        return _inner
