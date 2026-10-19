#!/bin/bash
source simulation/env.sh
cd dual
export GZ_IP=127.0.0.1
export ROS_LOCALHOST_ONLY=1

/usr/bin/gz sim -r -s dual_rescue.sdf --render-engine ogre > gz.log 2>&1 &
GZ_PID=$!

sleep 4
/usr/bin/gz topic -l > topics.txt

kill -9 $GZ_PID
cat topics.txt
