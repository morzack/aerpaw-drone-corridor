"""
aerpawlib script that controls each drone (independently)

communicates with ground station using http, docker stuff should handle other services (ex: mavproxy for downlink)
"""

import asyncio
import math
import requests
import os
import random

from aerpawlib.runner import StateMachine, state
from aerpawlib.util import VectorNED, Coordinate
from aerpawlib.vehicle import Drone

from lib.util import *
from lib.mapping import *

# TODO load from config
GROUND_HOST  = "http://ground-service:8080" if "GROUNDHOST" not in os.environ else os.environ["GROUNDHOST"]
MAV_HOST     = "127.0.0.1:5761" if "MAVHOST" not in os.environ else os.environ["MAVHOST"]
# GROUND_HOST = "http://127.0.0.1:8080"
# MAV_HOST = "127.0.0.1:5761"
DRONE_ID     = "DRONE-A" if "DRONEID" not in os.environ else os.environ["DRONEID"]
TARGET_COORD = Coordinate(*[float(i) for i in os.environ["TARGETCOORD"].split(",")], 0)

class PathingDrone(StateMachine):
    _world_map: MapBlockCoordSystem
    _target_coordinate: Coordinate

    @state(name="start", first=True)
    async def start(self, drone: Drone):
        # register w/ server
        # TODO these reqs should be asyncio safe somehow
        print("registering with GC...")
        resp = requests.post(
                url=f"{GROUND_HOST}/drone/add",
                json={
                    "id": DRONE_ID,
                    "connection": MAV_HOST,
                    })
        assert resp.status_code == 200

        # request map definition
        print("getting map params...")
        resp = requests.get(
                url=f"{GROUND_HOST}/drone/{DRONE_ID}/coordinates"
                )
        assert resp.status_code == 200
        j = resp.json()
        self._world_map = MapBlockCoordSystem(deserialize_coordinate(j["center"]), j["resolution"])
        
        self._target_coordinate = Coordinate(TARGET_COORD.lat, TARGET_COORD.lon, self._world_map._center_coords.alt)

        # wait a bit to make sure that the server grabs our location
        print("waiting to make sure server knows where we are...")
        await asyncio.sleep(5)

        return "requesting_takeoff"

    @state(name="requesting_takeoff")
    async def request_takeoff(self, drone: Drone):
        # ask server to take off
        print("requesting takeoff...")
        resp = requests.post(
                url=f"{GROUND_HOST}/drone/{DRONE_ID}/takeoff"
                )
        assert resp.status_code == 200
        j = resp.json()
        if not j["clear"]:
            print("GC said not to take off...")
            print("waiting ~5 sec and trying again")
            await asyncio.sleep(random.randint(2, 7))
            return "requesting_takeoff"

        # take off
        takeoff_alt = j["alt"]
        print(f"taking off to request alt of {takeoff_alt}...")
        await drone.takeoff(takeoff_alt)

        return "get_path"

    _path=None

    @state(name="get_path")
    async def request_path(self, drone: Drone):
        # ask server for path to target
        print("requesting path to target...")
        try:
            resp = requests.post(
                    url=f"{GROUND_HOST}/drone/{DRONE_ID}/pathfind",
                    json=serialize_coordinate(self._target_coordinate),
                    timeout=None                         # pathfinding is hard :)
                    )
        except Exception as e:
            print("failed to get path. timeout probable")
            print("using a random backoff")
            await asyncio.sleep(random.randint(3, 10))
            return "get_path"
        if resp.status_code == 400:
            print(f"no path to target {serialize_coordinate(self._target_coordinate)}")
            print(f"coord in block {self._world_map.coord_to_block(self._target_coordinate)}")
            print("waiting 5s and asking again")
            await asyncio.sleep(5)
            return "get_path"
        if resp.status_code != 200:
            print("request error. RTL")
            return "rtl"
        self._path = [deserialize_block(i) for i in resp.json()["path"]]
        print("path obtained:")
        print(self._path)
        return "next_node"

    @state(name="next_node")
    async def next_node(self, drone: Drone):
        # find next node in predetermined path
        print("finding next node in path")
        current_node = self._world_map.coord_to_block(drone.position)
        if current_node not in self._path:
            print("current node not in path. rerequesting a path and unreserving any blocks")
            resp = requests.post(
                    url=f"{GROUND_HOST}/drone/{DRONE_ID}/unreserve"
                    )
            if resp.status_code == 500:
                print("server error. unreservation failed. continuing")
            return "get_path"
        
        node_index = self._path.index(current_node)
        if node_index+1 == len(self._path):
            print("path complete. landing here")
            return "land"
        
        next_block = self._path[node_index+1]
        next_block_coords = self._world_map.get_block_center(next_block)
    
        # request permission to enter block
        resp = requests.post(
                url=f"{GROUND_HOST}/drone/{DRONE_ID}/reserve",
                json=serialize_block(next_block)
                )
        if resp.status_code != 200:
            print("error requesting next block.")
            print("backing off and trying again...")
            await asyncio.sleep(5)
            return "next_node"
        j = resp.json()
        if not j["success"]:
            print("reservation failed.")
            print("unreserving blocks, waiting 5s and requesting a new path...")
            resp = requests.post(
                    url=f"{GROUND_HOST}/drone/{DRONE_ID}/unreserve"
                    )
            if resp.status_code == 500:
                print("server error when unserving nodes. continuing")
            await asyncio.sleep(5)
            return "get_path"

        print(f"going to next block {next_block} @ {next_block_coords.lat, next_block_coords.lon, next_block_coords.alt}")
        await drone.goto_coordinates(next_block_coords)

        return "next_node"

    @state(name="rtl")
    async def rtl(self, drone: Drone):
        # return to the take off location
        print("returning to home coordinates, horizontally")
        print("WARNING: the drone is no longer respecting the ground systems")
        home_coords = Coordinate(
                drone.home_coords.lat, drone.home_coords.lon, drone.position.alt)
        await drone.goto_coordinates(home_coords)
        return "land"
    
    @state(name="land")
    async def land(self, drone: Drone):
        # land the drone, in place
        print("landing (not requesting permission)")
        await drone.land()
        print("done!")
