"""
ground station control code:

this opens a server of some kind that the drones communicate with.
supports:
    receiving notifs about drone pos
    reciving info about blockers
    querying corridors
    managing corridors
"""

import threading

from bottle import run

from aerpawlib.util import Coordinate

import ground.server as server
import ground.monitoring as monitoring
import ground.ground_logger as ground_logger

import lib.mapping as mapping
from lib.util import *

if __name__ == "__main__":
    server.world_map = mapping.WorldMap(Coordinate(35.7274488, -78.6960209, 30), 10)
    
    server.world_map.fill_map((-10, -40, -2), (10, 30, 2), Traversability.FREE)
    server.world_map.fill_map((-10, 0, -2), (10, 10, 2), Traversability.BLOCKED)
    server.world_map.fill_map((0, 0, -2), (2, 10, 2), Traversability.FREE)
    server.world_map.fill_map((-10, 0, -2), (10, 10, 0), Traversability.BLOCKED)

    server.logger = ground_logger.Logger(server.world_map)
    server.drones = monitoring.DroneListing(server.world_map, server.logger)
    
    stop = threading.Event()
    monitoring_daemon = server.drones.get_daemon_func(stop, 1)
    monitoring_thread = threading.Thread(target=monitoring_daemon)
    monitoring_thread.start()

    run(host='0.0.0.0', port=8080)
    stop.set()
