import random
import time
import threading

from raylib import *

from aerpawlib.util import Coordinate

from lib.mapping import *

from viewer.render import *
from viewer.api import *

RESOLUTION = (1000, 800)

InitWindow(RESOLUTION[0], RESOLUTION[1], b"drone viewer")
SetTargetFPS(60)

cameraPtr = ffi.new("struct Camera3D *")
camera = cameraPtr[0]

camera.position = [15., 0., 15.]
camera.target = [0., 2., 0.]
camera.up = [0., 1., 0.]
camera.fovy = 60.
camera.projection = CAMERA_PERSPECTIVE

# SetCameraMode(camera, CAMERA_FIRST_PERSON)
SetCameraMode(camera, CAMERA_FREE)
# SetCameraMode(camera, CAMERA_ORBITAL)

world = MapHandler("localhost:8080")
stop = threading.Event()
world_daemon = world.get_daemon_func(stop, 1)
world_daemon_thread = threading.Thread(target=world_daemon)
world_daemon_thread.start()

while not WindowShouldClose():
    UpdateCamera(cameraPtr)
    
    BeginDrawing()
    
    ClearBackground(RAYWHITE)
    
    BeginMode3D(camera)
    reset_outlines()
    world.render_map(camera)
    
    EndMode3D()
    
    EndDrawing()
CloseWindow()
stop.set()
