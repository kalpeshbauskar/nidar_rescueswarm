#!/bin/bash
pkill -f px4 2>/dev/null || true
pkill -f gz 2>/dev/null || true
pkill -f MicroXRCEAgent 2>/dev/null || true
rm -f run.lock
bash run.sh > run_output.log 2>&1
