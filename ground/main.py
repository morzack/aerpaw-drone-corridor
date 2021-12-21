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

import server
import monitoring
import mapping
from util import *

if __name__ == "__main__":
    server.world_map = mapping.WorldMap(Coordinate(35.7274488, -78.6960209, 100), 10)
    
    server.world_map.fill_map((-50, -50, -2), (50, 50, 2), Traversability.FREE)
    server.world_map.fill_map((5, -50, -2), (5, 50, 1), Traversability.BLOCKED)
    server.world_map.fill_map((5, -50, 2), (5, 49, 2), Traversability.BLOCKED)

    server.drones = monitoring.DroneListing(server.world_map)
    
    stop = threading.Event()
    monitoring_daemon = server.drones.get_daemon_func(stop, 1)
    monitoring_thread = threading.Thread(target=monitoring_daemon)
    monitoring_thread.start()

    run(host='localhost', port=8080)
    stop.set()
