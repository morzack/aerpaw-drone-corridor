#!/usr/bin/bash

id="droneA"

curl -X POST "http://localhost:8080/drone/$id/pathfind" \
  -H "Content-Type: application/json" \
  --data '{"lat": 35.7274073, "lon": -78.6949836, "alt": 100}'
