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
    server.world_map = mapping.WorldMap(Coordinate(35.7274488, -78.6960209, 30), 10)
    
    server.world_map.fill_map((-10, -10, -2), (20, 20, 2), Traversability.FREE)
    server.world_map.fill_map((5, -10, -2), (5, 20, 1), Traversability.BLOCKED)
    server.world_map.fill_map((5, -10, 2), (5, 19, 2), Traversability.BLOCKED)

    server.drones = monitoring.DroneListing(server.world_map)
    
    stop = threading.Event()
    monitoring_daemon = server.drones.get_daemon_func(stop, 1)
    monitoring_thread = threading.Thread(target=monitoring_daemon)
    monitoring_thread.start()

    run(host='0.0.0.0', port=8080)
    stop.set()
