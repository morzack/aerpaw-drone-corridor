import time

from lxml import etree
from pykml.parser import Schema
from pykml.factory import KML_ElementMaker as KML
from pykml.factory import GX_ElementMaker as GX

from quad_mesh_simplify import simplify_mesh
import numpy as np

from aerpawlib.util import Coordinate, VectorNED

from lib.util import *
from lib.mapping import WorldMap

drone_colors = {
        "drone1": "ff0000ff",
        "drone2": "ff00ff00",
        "drone3": "ffff0000",
        "drone4": "ffffff00",
        "drone5": "ff00ffff",
        "drone6": "ffff00ff",
        }

drone_poly_scale_x = 0.00001
drone_poly_scale_y = 0.00001

drone_poly = [
        [[0, 0, 0], [0, 0.5, -1], [0, 1, 0]],
        [[0, 0, 0], [0, -0.5, -1], [0, -1, 0]],
        [[1, 0, 0], [1, 0.5, -1], [1, 1, 0]],
        [[1, 0, 0], [1, -0.5, -1], [1, -1, 0]],
        ]

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
        targeting = Traversability.FREE # or BLOCKED
        for block_coord in coords_searching:
            if block_coord in m and m[block_coord] == targeting:
                continue
            
            corners = _get_corners(block_coord)
            for adj in _get_adj(block_coord):
                if adj in m and m[adj] == targeting:
                    # add face
                    points = list(corners & _get_corners(adj))
                    # share [0] and [1]
                    t_1 = tuple(sorted([points[0], points[1], points[2]]))
                    t_2 = tuple(sorted([points[0], points[1], points[3]]))
                    triangles |= {t_1, t_2}

        # simplify mesh
        # find corners/faces a la obj
        positions = []
        faces = []
        for t in triangles:
            f = []
            for c in t:
                if c not in positions:
                    positions.append(c)
                f.append(positions.index(c))
            faces.append(f)
        positions, faces = simplify_mesh(np.array(positions), np.array(faces, dtype=np.uint32), 600)
        
        # # find distinct submeshes to avoid simplification issues
        # submeshes = [] # collection of collection of corner idxs
        # accounted = set() # flattened ^
        
        # def _recursive_find_corners(corner_idx, corner_group, depth=0, max_depth=40):
        #     if corner_idx in accounted:
        #         return
        #     if depth >= max_depth:
        #         return
        #     # get triangle corners w/ this corner
        #     cors = set()
        #     for f_idx, face in enumerate(faces):
        #         if corner_idx in face:
        #             corner_group.append(face)
        #             cors |= set(face)
        #     accounted.add(corner_idx)
        #     for c in cors:
        #         _recursive_find_corners(c, corner_group, depth+1)

        # for c_idx, corner in enumerate(corners):
        #     s = []
        #     _recursive_find_corners(c_idx, s)
        #     print(s)
        #     if len(s) != 0:
        #         submeshes.append(s)

        # triangles = []
        # for submesh in submeshes:
        #     new_positions, new_face = simplify_mesh(np.array(corners), np.array(submesh), 30)
        #     for face in new_face:
        #         triangles.append([new_positions[i] for i in face])
        # print(triangles)

        # convert triangles to world space
        def _coord_to_world_raw(coord):
            x, y, z = [i*self._world_map._resolution for i in coord]
            delta_vec = VectorNED(y, x, -z)
            return self._world_map._center_coords + delta_vec

        # world_triangles = []
        # for triangle in triangles:
        #     c1, c2, c3 = [_coord_to_world_raw(c) for c in triangle]
        #     world_triangles.append((c1, c2, c3))
        
        world_triangles = []
        for triangle in faces:
            c1, c2, c3 = [_coord_to_world_raw(positions[c]) for c in triangle]
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
            
            adding_style = KML.Style(
                    KML.id(f"{drone}_sty"),
                    KML.LineStyle(
                        KML.color(drone_colors.get(drone, "ff00aaff")),
                        KML.width(10),
                        )
                    )
            r.append(adding_style)

            d_poly = []
            for tri in drone_poly:
                t = []
                for node in tri:
                    x, y, alt = node
                    x *= drone_poly_scale_x
                    y *= drone_poly_scale_y
                    i = unique_tiles[-1]
                    x += i[2].lon
                    y += i[2].lat
                    alt += i[2].alt
                    t.append([x, y, alt])
                d_poly.append(t)
            
            for tri in d_poly:
                cs = [*tri] + [tri[0]]
                r.append(KML.Placemark(
                        KML.styleUrl(f"#{drone}_sty"),
                        KML.LineString(
                            GX.altitudeMode("relativeToGround"),
                            KML.coordinates("\n".join([f"{j[0]},{j[1]},{j[2]}" for j in cs]))
                            )
                        ))

            adding = KML.Placemark(
                    KML.name(f"{drone} path"),
                    KML.styleUrl(f"#{drone}_sty"),
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
