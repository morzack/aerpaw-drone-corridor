# TODO restructure so serialization/deserialization are standard as well as mapping stuff

from typing import Tuple

from aerpawlib.util import Coordinate, VectorNED

MapBlockCoord = Tuple[int, int, int]    # coord in x, y, z measuring blocks away from central block
                                        # note that +x = east, +y = north, +z = up

def serialize_coordinate(c: Coordinate):
    return {
            "lat": c.lat,
            "lon": c.lon,
            "alt": c.alt,
            }

def deserialize_coordinate(x) -> Coordinate:
    return Coordinate(x["lat"], x["lon"], x["alt"])

def serialize_block(b: MapBlockCoord):
    return {
            "x": b[0],
            "y": b[1],
            "z": b[2],
            }

def deserialize_block(x) -> MapBlockCoord:
    return (x["x"], x["y"], x["z"])

class WorldMap:
    def __init__(self, center_coords: Coordinate, resolution: float):
        self._center_coords = center_coords
        self._resolution = resolution

    def coord_to_block(self, coord: Coordinate) -> MapBlockCoord:
        delta_vec = coord - self._center_coords
        x, y, z = [int(i // self._resolution) for i in [delta_vec.east, delta_vec.north, -delta_vec.down]]
        return (x, y, z)

    def block_to_coord(self, block: MapBlockCoord) -> Coordinate:
        """
        returns the coordinate representing the corner of the block
        """
        x, y, z = [i*self._resolution for i in block]
        delta_vec = VectorNED(y, x, -z)
        return self._center_coords + delta_vec

    def get_block_center(self, block: MapBlockCoord) -> Coordinate:
        x, y, z = [i*self._resolution for i in block]
        x, y, z = [i+(0.5 * self._resolution) for i in [x,y,z]]
        delta_vec = VectorNED(y, x, -z)
        return self._center_coords + delta_vec
