import time
import os
import signal
import subprocess

log_file = "training/training.log"

print("Waiting for epoch 4 to start...")
while True:
    with open(log_file, 'r') as f:
        log_content = f.read()
    if "4/50" in log_content:
        print("Epoch 4 started, sending SIGINT to train_v2.py...")
        # Find the PID of python3 training/train_v2.py
        try:
            pid_str = subprocess.check_output(["pgrep", "-f", "python3 training/train_v2.py"]).decode().strip()
            for pid in pid_str.split():
                os.kill(int(pid), signal.SIGINT)
                print(f"Sent SIGINT to {pid}")
            break
        except Exception as e:
            print(f"Failed to find or kill process: {e}")
            break
    time.sleep(5)
