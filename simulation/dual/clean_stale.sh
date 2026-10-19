#!/usr/bin/env bash
PORT=8898
echo "PORT STATUS BEFORE START:"
if lsof -i UDP:$PORT > /dev/null 2>&1; then
    echo "OCCUPIED"
    echo "Stale processes on UDP $PORT:"
    lsof -i UDP:$PORT
    
    # Kill NIDAR-owned MicroXRCEAgent
    pids=$(lsof -t -i UDP:$PORT)
    for pid in $pids; do
        if ps -p $pid -o cmd | grep -q "MicroXRCEAgent"; then
            echo "Killing stale NIDAR MicroXRCEAgent (PID $pid)..."
            kill -9 $pid
        fi
    done
else
    echo "FREE"
fi

# We can also check for stale gz / px4
gz_pids=$(pgrep -f "gz sim.*dual_rescue.sdf")
if [ ! -z "$gz_pids" ]; then
    echo "Killing stale Gazebo instances: $gz_pids"
    kill -9 $gz_pids
fi

px4_pids=$(pgrep -f "px4 -i .* -s etc/init.d-posix/rcS")
if [ ! -z "$px4_pids" ]; then
    echo "Killing stale PX4 instances: $px4_pids"
    kill -9 $px4_pids
fi

echo "MICROXRCE PORT: $PORT"
