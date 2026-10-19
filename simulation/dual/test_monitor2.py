import curses, json, time, math, os, sys, rclpy
from std_msgs.msg import String
from gz.transport13 import Node as GzNode
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.msgs10.actuators_pb2 import Actuators
sys.path.append('.')
from telemetry_monitor import TelemetryMonitor, draw_dashboard

rclpy.init()
node = TelemetryMonitor()

start_t = time.time()
while time.time() - start_t < 35:
    rclpy.spin_once(node, timeout_sec=0.1)
    if node.drones[1] and node.drones[2] and node.gz_actuators[1]["vel"]:
        if sum(node.gz_actuators[1]["vel"]) > 100:
            break

class DummyStdscr:
    def __init__(self): self.lines = {}
    def erase(self): self.lines = {}
    def getmaxyx(self): return (100, 100)
    def addstr(self, y, x, text):
        if y not in self.lines: self.lines[y] = {}
        self.lines[y][x] = text
    def refresh(self): pass
    def nodelay(self, b): pass
    def getch(self): return ord('q')

stdscr = DummyStdscr()
try:
    draw_dashboard(stdscr, node)
except Exception as e:
    pass

for y in sorted(stdscr.lines.keys()):
    row = stdscr.lines[y]
    line = ""
    for x in sorted(row.keys()):
        line += " " * (x - len(line)) + str(row[x])
    print(line)

node.destroy_node()
rclpy.shutdown()
