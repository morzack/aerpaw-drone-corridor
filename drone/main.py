"""
aerpawlib script that controls each drone (independently)

communicates with ground station using http, docker stuff should handle other services (ex: mavproxy for downlink)
"""

import asyncio
import math
import requests

from aerpawlib.runner import StateMachine, state
from aerpawlib.util import VectorNED, Coordinate
from aerpawlib.vehicle import Drone

from util import *

# TODO load from config
GROUND_HOST  = "http://ground-service"
MAV_HOST     = "tcp:drone-1:5100"
DRONE_ID     = "DRONE-A"

class PathingDrone(StateMachine):
    _target_coordinate: Coordinate
    _world_map: WorldMap

    @state(name="start", first=True)
    async def start(self, drone: Drone):
        # register w/ server
        # TODO these reqs should be asyncio safe somehow
        print("registering with GC...")
        resp = requests.post(
                url=f"{GROUND_HOST}/drone/add",
                data={
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
        self._world_map = WorldMap(deserialize_coordinate(j["center"]), j["resolution"])

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
            print("waiting 5 sec and trying again")
            await asyncio.sleep(5)
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
        resp = requests.post(
                url=f"{GROUND_HOST}/drone/{DRONE_ID}/pathfind",
                data=serialize_coordinate(_target_coordiante)
                )
        if resp.status_code == 400:
            print("no path to target.")
            print("waiting 5s and asking again")
            await asyncio.sleep(5)
            return "get_path"
        if resp.status_code != 200:
            print("request error. RTL")
            return "rtl"
        self._path = resp.json()
        print("path obtained:")
        print(self._path)
        return "next_node"

    @state(name="next_node")
    async def next_node(self, drone: Drone):
        # find next node in predetermined path
        print("finding next node in path")
        current_node = self._world_map.coord_to_block(drone.position)
        if current_node not in path:
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
        
        next_block = self._path[current_node+1]
        next_block_coords = self._world_map.get_block_center(next_block)
    
        # request permission to enter block
        resp = requests.post(
                url=f"{GROUND_HOST}/drone/{DRONE_ID}/reserve",
                data=serialize_block(next_block)
                )
        if resp.status_code != 200:
            print("error requesting next block.")
            print("backing off and trying again...")
            await asyncio.sleep(5)
            return "next_node"
        j = resp.json()
        if not j["success"]:
            print("reservation failed.")
            print("unreserving blocks, waiting 5s and trying again...")
            resp = requests.post(
                    url=f"{GROUND_HOST}/drone/{DRONE_ID}/unreserve"
                    )
            if resp.status_code == 500:
                print("server error when unserving nodes. continuing")
            await asyncio.sleep(5)
            return "next_node"

        print(f"going to next block {next_block} @ {next_block_coords}")
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
