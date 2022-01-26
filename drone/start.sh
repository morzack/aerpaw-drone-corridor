#!/bin/bash
set -m

# 5760 -- aerpawlib
# 5761 -- ground mav
# 5762 -- qgc
screen -S mavproxy -dm mavproxy.py \
    --master tcp:sitl:$PORT \
    --out :5760 \
    --out ground-service:$GROUNDPORT \
    --out tcpin::5762 \
    --source-system=$SYSID

sleep 5

python3.8 -u -m aerpawlib --conn :5760 --vehicle drone --script drone
