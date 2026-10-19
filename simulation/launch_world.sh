#!/usr/bin/env bash
set -e
source /home/kalpeshbauskar/nidar_rescueswarm/simulation/env.sh
exec /usr/bin/gz sim --render-engine ogre -r /home/kalpeshbauskar/nidar_rescueswarm/simulation/worlds/flood_zone_drone.sdf "$@"
