# Drone corridor experiment

tl;dr

there are *n* drones and a ground station.
the ground station determines a point *a* and *b* that the drones are moving between.
the ground station creates a "corridor" that the drones can fly through.
the drones move to/along the corridor.

if something gets stuck in the corridor, the drones should dynamically stop and avoid collisions.
i.e., each drone is independent + aware of the others.
furthermore, each drone has some kind of sensing to detect potential hazards (relayed to the ground station).

in the case of an obstacle:

* the first drone should stop because of a potential collision
* drones behind the first should stop because the first drone has stopped
* the GCS should be notified by each drone that there's an obstruction
* the GCS should create a new corridor and forward it to each drone
* the drones should then independently figure out how to move through the corridor

## implementation

this is implementing using a block system.
the controlled airspace is defined using a center coordinate, and a size for each block.
each block only allows one drone to occupy it, and drones must request permission to move into adjacent blocks.
the central controller ensures that every block adjacent to a drone is cleared out.
the central controller also provides functionality to generate a path plan for a drone using a basic pathfinder.

## running

```
docker-compose build

docker-compose up
```

you'll need to connect to each drone and set the following param:

```
mavproxy.py --master=tcp::14551

param set DISARM_DELAY 0
```

there's an open mavproxy port for each drone at `tcp:0.0.0.0:14551...n`.
this can be used for qgroundcontrol
