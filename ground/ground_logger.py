import time

from lxml import etree
from pykml.parser import Schema
from pykml.factory import KML_ElementMaker as KML
from pykml.factory import GX_ElementMaker as GX

from aerpawlib.util import Coordinate, VectorNED

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
        doc = KML.kml(
                KML.Document(
                    KML.Name("drone paths")
                    )
                )
        for a in self._serialize_kml_drones():
            doc.Document.append(a)
        for b in self._serialize_kml_blocks():
            doc.Document.append(b)
        return etree.tostring(doc, pretty_print=True)

    def _serialize_kml_blocks(self):
        # calculate polys for each block
        # iterate over the entire airspace, find adjacencies, add faces
        m = self._world_map._map.copy() # to avoid race conditions ugh
        kml_polys = []
        
        def _get_bounds(idx):
            vs = {i[idx] for i in m}
            return range(min(vs)-1, max(vs)+2)
        x_bounds, y_bounds, z_bounds = [_get_bounds(i) for i in range(3)]
        
        coords_searching = set()
        for x in x_bounds:
            for y in y_bounds:
                for z in z_bounds:
                    coords_searching.add((x, y, z))

        def _get_adj(coord):
            x, y, z = coord
            return {
                    (x+1, y, z),
                    (x-1, y, z),
                    (x, y+1, z),
                    (x, y-1, z),
                    (x, y, z+1),
                    (x, y, z-1)
                    }
        
        def _get_corners(coord):
            # get corners of a unit cube. assume that coord given is in center
            cube_size = 1
            delta = cube_size / 2
            x, y, z = coord
            return {
                    (x+delta, y+delta, z+delta),
                    (x+delta, y+delta, z-delta),
                    (x+delta, y-delta, z+delta),
                    (x+delta, y-delta, z-delta),
                    (x-delta, y+delta, z+delta),
                    (x-delta, y+delta, z-delta),
                    (x-delta, y-delta, z+delta),
                    (x-delta, y-delta, z-delta),
                    }

        def _normalize_point(point):
            # to account for floating point fun
            x, y, z = point
            return (round(x, 1), round(y, 1), round(z, 1))

        triangles = set()
        for block_coord in coords_searching:
            if block_coord in m and m[block_coord] == Traversability.BLOCKED:
                continue
            
            corners = _get_corners(block_coord)
            for adj in _get_adj(block_coord):
                if adj in m and m[adj] == Traversability.BLOCKED:
                    # add face
                    points = list(corners & _get_corners(adj))
                    # share [0] and [1]
                    t_1 = tuple(sorted([points[0], points[1], points[2]]))
                    t_2 = tuple(sorted([points[0], points[1], points[3]]))
                    triangles |= {t_1, t_2}

        # convert triangles to world space
        def _coord_to_world_raw(coord):
            x, y, z = [i*self._world_map._resolution for i in coord]
            delta_vec = VectorNED(y, x, -z)
            return self._world_map._center_coords + delta_vec

        world_triangles = []
        for triangle in triangles:
            c1, c2, c3 = [_coord_to_world_raw(c) for c in triangle]
            world_triangles.append((c1, c2, c3))

        # convert coordinates defining poly tris to lines to be rendered in KML
        adding = []
        for tri in world_triangles:
            cs = [*tri] + [tri[0]]
            adding.append(KML.Placemark(
                    KML.LineString(
                        GX.altitudeMode("relativeToGround"),
                        KML.coordinates("\n".join([f"{i.lon},{i.lat},{i.alt}" for i in cs]))
                        )
                    ))
        return adding

    def _serialize_kml_drones(self):
        # get kml w/ each drone's path, caring only about the blocks and time
        r = []
        for drone in self._drone_log:
            path = self._drone_log[drone]
            unique_tiles = []
            for i in path:
                if len(unique_tiles) != 0:
                    last_tile = unique_tiles[-1][1]
                    if last_tile == i[1]:
                        continue
                unique_tiles.append((i[0], i[1], self._world_map.block_to_coord(i[1])))
            
            adding = KML.Placemark(
                    KML.name(f"{drone} path"),
                    KML.LineString(
                        # KML.extrude(1),
                        KML.tessellate(1),
                        GX.altitudeMode("relativeToGround"),
                        KML.coordinates("\n".join([f"{i[2].lon},{i[2].lat},{i[2].alt}" for i in unique_tiles]))
                        )
                    )
            r.append(adding)
        return r

    def save(self, filename: str):
        with open(filename, 'w') as f:
            f.write(self.serialize_kml)
