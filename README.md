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
