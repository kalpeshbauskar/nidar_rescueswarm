import curses, json, time, math, os, sys, rclpy
from std_msgs.msg import String
from gz.transport13 import Node as GzNode
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.msgs10.actuators_pb2 import Actuators
from telemetry_monitor import TelemetryMonitor
rclpy.init()
node = TelemetryMonitor()
start_t = time.time()
while time.time() - start_t < 40:
    rclpy.spin_once(node, timeout_sec=0.1)
    if node.drones[1] and node.drones[2] and node.gz_actuators[1]["vel"]:
        if sum(node.gz_actuators[1]["vel"]) > 100:
            print("D1 VEL:", node.gz_actuators[1]["vel"])
            print("D2 VEL:", node.gz_actuators[2]["vel"])
            print("D1 PAYLOAD:", node.drones[1].get('payload'))
            break
print("DONE")
