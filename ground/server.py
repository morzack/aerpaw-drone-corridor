from bottle import route, run, request, abort
import json

from aerpawlib.util import Coordinate

from mapping import WorldMap
from util import *

world_map: WorldMap = None

@route('/drone/<id>/pathfind', method='POST')
def pathfind(id):
    if request.json == None:
        abort(400, "plz gib json")
    block_from = world_map.drone_block(id)
    if block_from == None:
        abort(404, "drone not found")
    lat = request.json["lat"]
    lon = request.json["lon"]
    alt = request.json["alt"]
    target_coords = Coordinate(lat, lon, alt)
    block_to = world_map.coord_to_block(target_coords)
    print(block_to)
    print(block_from)
    path = world_map.find_path(block_from, block_to, {id})
    if path == None:
        abort(400, "no path sadge :(")
    return json.dumps(path)

if __name__ == "__main__":
    # for testing tehe :P
    world_map = WorldMap(Coordinate(35.7274488, -78.6960209, 100), 10)
    world_map.fill_map((-50, -50, -2), (50, 50, 2), Traversability.FREE)
    world_map.fill_map((5, -50, -2), (5, 50, 1), Traversability.BLOCKED)
    world_map.fill_map((5, -50, 2), (5, 49, 2), Traversability.BLOCKED)
    world_map.update_drone("droneA", Coordinate(35.7274488, -78.6960209, 100))
    
    run(host='localhost', port=8080)
