import json, time, math, os, sys
import rclpy
from std_msgs.msg import String
from gz.transport13 import Node as GzNode
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.msgs10.actuators_pb2 import Actuators

rclpy.init()
class DummyNode: pass
node = DummyNode()
node.drones = {1: None, 2: None}
node.gz_poses = {}
node.gz_actuators = {1: {"vel": None, "time": 0}, 2: {"vel": None, "time": 0}}

r_node = rclpy.create_node('dummy')
r_node.create_subscription(String, '/swarm/drone1/state', lambda m: update_d(1, m), 10)
r_node.create_subscription(String, '/swarm/drone2/state', lambda m: update_d(2, m), 10)

def update_d(i, msg):
    node.drones[i] = json.loads(msg.data)
    node.drones[i]['rx_time'] = time.time()

gz = GzNode()
def pose_cb(msg):
    now = time.time()
    for p in msg.pose:
        if p.name.startswith('parcel'):
            node.gz_poses[p.name] = {"alt": p.position.z, "time": now}
gz.subscribe(Pose_V, '/world/dual_rescue/dynamic_pose/info', pose_cb)

def act_cb(idx, msg):
    node.gz_actuators[idx] = {"vel": list(msg.velocity), "time": time.time()}
gz.subscribe(Actuators, '/rescue_0/command/motor_speed', lambda m: act_cb(1, m))
gz.subscribe(Actuators, '/rescue_1/command/motor_speed', lambda m: act_cb(2, m))

start_t = time.time()
while time.time() - start_t < 25:
    rclpy.spin_once(r_node, timeout_sec=0.1)
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

# call the draw logic (we have to copy it or import it)
sys.path.append('.')
from telemetry_monitor import draw_dashboard
try:
    draw_dashboard(stdscr, node)
except Exception as e:
    pass

for y in sorted(stdscr.lines.keys()):
    row = stdscr.lines[y]
    line = ""
    for x in sorted(row.keys()):
        line += " " * (x - len(line)) + row[x]
    print(line)

r_node.destroy_node()
rclpy.shutdown()
