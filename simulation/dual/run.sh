#!/usr/bin/env bash
set -e
source /home/kalpeshbauskar/nidar_rescueswarm/simulation/env.sh
exec python /home/kalpeshbauskar/nidar_rescueswarm/simulation/dual/run.py "$@"
