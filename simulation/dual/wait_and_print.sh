#!/bin/bash
echo "Waiting for task-291 (run_5ms.py) to finish..."
while kill -0 $(pgrep -f run_5ms.py | head -n 1) 2>/dev/null; do
    sleep 5
done
echo "Finished!"
cat wind_5_report.txt
