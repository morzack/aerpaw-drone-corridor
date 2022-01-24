#!/usr/bin/bash

id="droneA"

# curl -X POST "http://localhost:8080/drone/add" \
#   -H "Content-Type: application/json" \
#   --data '{"id": "a", "connection": "127.0.0.1:5761"}'

# curl -X POST "http://localhost:8080/drone/add" \
#   -H "Content-Type: application/json" \
#   --data '{"id": "a", "connection": "127.0.0.1:5761"}'

# curl -X POST "http://localhost:8080/drone/$id/pathfind" \
#   -H "Content-Type: application/json" \
#   --data '{"lat": 35.7274073, "lon": -78.6949836, "alt": 100}'

curl -X GET "http://localhost:8080/log/kml"

# curl -X POST "http://localhost:8080/map/update" \
#   -H "Content-Type: application/json" \
#   --data '{"a": {"x":-3, "y":0, "z":-2}, "b": {"x":3, "y":10, "z":2}, "empty": false}'

# curl -X POST "http://localhost:8080/map/update" \
#   -H "Content-Type: application/json" \
#   --data '{"a": {"x":-3, "y":0, "z":-2}, "b": {"x":3, "y":10, "z":2}, "empty": true}'
