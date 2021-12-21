from bottle import route, run, request, abort

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
    target_coords = deserialize_coordinate(request.json)
    block_to = world_map.coord_to_block(target_coords)
    print(f"plotting path from {block_from} to {block_to} for drone {id}")
    path = world_map.find_path(block_from, block_to, {id})
    if path == None:
        abort(400, "no path sadge :(")
    return path

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
    if request.json == None:
        abort(400, "plz gib json")
    block_removing = deserialize_block(request.json)
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

if __name__ == "__main__":
    # for testing tehe :P
    world_map = WorldMap(Coordinate(35.7274488, -78.6960209, 100), 10)
    world_map.fill_map((-50, -50, -2), (50, 50, 2), Traversability.FREE)
    world_map.fill_map((5, -50, -2), (5, 50, 1), Traversability.BLOCKED)
    world_map.fill_map((5, -50, 2), (5, 49, 2), Traversability.BLOCKED)
    world_map.update_drone("droneA", Coordinate(35.7274488, -78.6960209, 100))

    run(host='localhost', port=8080)
