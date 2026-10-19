#!/usr/bin/env bash
set -e
source /home/kalpeshbauskar/nidar_rescueswarm/simulation/env.sh
export PATH=/usr/bin:/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin:$PATH
export PX4_SYS_AUTOSTART=4025
export PX4_GZ_STANDALONE=1
export PX4_GZ_WORLD=flood_zone
export PX4_GZ_MODEL_NAME=x500_claw_0
export PX4_SIM_MODEL=gz_x500_claw
export PX4_UXRCE_DDS_PORT=8899
export PX4_GZ_SIM_RENDER_ENGINE=ogre
cd /home/kalpeshbauskar/nidar_rescueswarm/simulation/px4-runtime
exec /home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin/px4 -i 0 -s etc/init.d-posix/rcS . "$@"
