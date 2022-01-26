from bottle import route, run, request, abort

from aerpawlib.util import Coordinate

from lib.mapping import WorldMap
from lib.util import *

from ground.monitoring import DroneConnection, DroneListing
from ground.ground_logger import Logger

world_map: WorldMap = None
drones: DroneListing = None
logger: Logger = None

@route('/drone/<id>/pathfind', method='POST')
def pathfind(id):
    if request.json == None:
        abort(400, "plz gib json")
    block_from = world_map.drone_block(id)
    if block_from == None:
        abort(404, "drone not found")
    target_coords = deserialize_coordinate(request.json)
    block_to = world_map.coord_to_block(target_coords)
    print(f"plotting path from {block_from} to {block_to} for drone {id}")
    path = world_map.find_path(block_from, block_to, {id})
    if path == None:
        abort(400, "no path sadge :(")
    return {"path": [serialize_block(i) for i in path]}

@route('/drone/<id>/takeoff', method='POST')
def request_takeoff(id):
    # send alt to take off to and enter airspace, if safe
    # also request block as part of this
    drone_block = world_map.drone_block(id)
    heightslice = world_map.heightslice(drone_block)
    # attempt to take off into lowest
    target_block = heightslice[0]
    success = world_map.reserve_block(id, target_block, skip_adj=True)
    target_alt = world_map.block_to_coord(target_block).alt + world_map._resolution/2
    return {
        "clear": success,
        "alt": None if not success else target_alt
        }

@route('/viewer/coordinates', method='GET')
def define_coord_system():
    # get parameters defining coordinate system [center and resolution]
    return {
        "center": serialize_coordinate(world_map._center_coords),
        "resolution": world_map._resolution
        }

@route('/drone/<id>/coordinates', method='GET')
def define_coord_system(id):
    # get parameters defining coordinate system [center and resolution]
    return {
        "center": serialize_coordinate(world_map._center_coords),
        "resolution": world_map._resolution
        }

@route('/drone/<id>/reserve', method='POST')
def reserve_block(id):
    if request.json == None:
        abort(400, "plz gib json")
    block_reserving = deserialize_block(request.json)
    success = world_map.reserve_block(id, block_reserving)
    return {"success": success}

@route('/drone/<id>/unreserve', method='POST')
def unreserve_block(id):
    # given a block, attempt to reserve
    if request.json != None:
        block_removing = deserialize_block(request.json)
    else:
        block_removing = None
        for b in world_map._occupied_blocks:
            if world_map._occupied_blocks[b] == id:
                block_removing = b
                break
    if block_removing == None:
        abort(400, "no block to remove")
    success = world_map.unreserve_block(id, block_removing)
    return {"success": success}

@route('drone/<id>/get_reserved')
def get_reserved(id):
    # get a drone's reserved block
    b = None
    for block in world_map._occupied_blocks:
        if world_map._occupied_blocks[block] == id:
            b = block
            break
    return serialize_block(b)

@route('/drone/<id>/can_reserve', method='POST')
def can_reserve(id):
    # given a list of blocks, return ones that can be reserved/moved into
    if request.json == None:
        abort(400, "plz gib json")
    blocks = [deserialize_block(i) for i in request.json]
    possible = [world_map.can_reserve_block(id, block) for block in blocks]
    return possible

@route('/drone/add', method='POST')
def add_drone():
    if request.json == None:
        abort(400, "plz gib json")
    id = request.json["id"]
    conn_str = request.json["connection"]
    drones.add_drone(id, conn_str)

@route('/log/kml', method='GET')
def get_drone_paths():
    kml = logger.serialize_kml()
    return kml

@route('/viewer/map', method='GET')
def get_map():
    map_blocks = []
    map_occupied = []

    for block in world_map._map:
        map_blocks.append({
            "block": serialize_block(block),
            "val": world_map._map[block].value,
            })
    
    for drone_name in world_map._drone_locations:
        drone = world_map._drone_locations[drone_name]
        map_occupied.append({
            "block": serialize_block(world_map.coord_to_block(drone)),
            "val": drone_name,
            })

    return {
            "blocks": map_blocks,
            "occupied": map_occupied,
            }

@route('/map/update', method='POST')
def update_map():
    if request.json == None:
        abort(400, "plz gib json")
    a = deserialize_block(request.json["a"])
    b = deserialize_block(request.json["b"])
    traversability = Traversability.FREE if request.json["empty"] else Traversability.BLOCKED
    world_map.fill_map(a, b, traversability)

if __name__ == "__main__":
    # for testing tehe :P
    world_map = WorldMap(Coordinate(35.7274488, -78.6960209, 100), 10)
    world_map.fill_map((-50, -50, -2), (50, 50, 2), Traversability.FREE)
    world_map.fill_map((5, -50, -2), (5, 50, 1), Traversability.BLOCKED)
    world_map.fill_map((5, -50, 2), (5, 49, 2), Traversability.BLOCKED)
    world_map.update_drone("droneA", Coordinate(35.7274488, -78.6960209, 100))

    run(host='localhost', port=8080)
