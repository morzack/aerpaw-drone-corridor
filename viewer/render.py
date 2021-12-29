from raylib import *

from lib.mapping import *

drawn_outlines = []
def reset_outlines():
    global drawn_outlines
    drawn_outlines = []

def draw_cube(camera, pos, color, world_map: WorldMap, text: str=""):
    global drawn_outlines
    for adj in adjacent_blocks(pos).keys():
        posadj = [-adj[0], adj[2], adj[1]]
        if adj not in world_map._map:
            continue
        if adj in drawn_outlines:
            continue
        DrawCubeWires(posadj, 1., 1., 1., GRAY)
        drawn_outlines.append(adj)
    pos = [-pos[0], pos[2], pos[1]]
    DrawCube(pos, 1., 1., 1., color)
    DrawCubeWires(pos, 1., 1., 1., BLACK)
    if text != "":
        EndMode3D()
        text_pos = [pos[0], pos[1] + .5, pos[2]]
        screen_pos = GetWorldToScreen(text_pos, camera)
        text = text.encode('utf-8')
        DrawText(text, int(screen_pos.x) - MeasureText(text, 30)//2, int(screen_pos.y), 30, BLACK)
        BeginMode3D(camera)
