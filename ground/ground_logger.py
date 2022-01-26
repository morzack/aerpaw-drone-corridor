import time

from lxml import etree
from pykml.parser import Schema
from pykml.factory import KML_ElementMaker as KML
from pykml.factory import GX_ElementMaker as GX

from aerpawlib.util import Coordinate

from lib.util import *
from lib.mapping import WorldMap

class Logger:
    def __init__(self, world_map: WorldMap):
        self._drone_log = {}
        self._world_map = world_map

    def update_drone(self, drone_id: str, drone_block: MapBlockCoord):
        if drone_id not in self._drone_log:
            self._drone_log[drone_id] = []
        self._drone_log[drone_id].append((time.time(), drone_block))

    def serialize_kml(self) -> str:
        # get kml w/ each drone's path, caring only about the blocks and time
        drone_paths = {}
        for drone in self._drone_log:
            path = self._drone_log[drone]
            unique_tiles = []
            for i in path:
                if len(unique_tiles) != 0:
                    last_tile = unique_tiles[-1][1]
                    if last_tile == i[1]:
                        continue
                unique_tiles.append((i[0], i[1], self._world_map.block_to_coord(i[1])))
            drone_paths[drone] = unique_tiles
    
        doc = KML.kml(
                KML.Document(
                    KML.Name("drone paths")
                    )
                )
        for drone in drone_paths:
            path = drone_paths[drone]
            adding = KML.Placemark(
                    KML.name(f"{drone} path"),
                    KML.LineString(
                        # KML.extrude(1),
                        KML.tessellate(1),
                        GX.altitudeMode("relativeToGround"),
                        KML.coordinates("\n".join([f"{i[2].lon},{i[2].lat},{i[2].alt}" for i in path]))
                        )
                    )
            doc.Document.append(adding)
        return etree.tostring(doc, pretty_print=True)
    
    def save(self, filename: str):
        with open(filename, 'w') as f:
            f.write(self.serialize_kml)
