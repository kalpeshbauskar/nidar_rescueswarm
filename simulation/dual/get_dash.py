import curses, json, time, math, os, sys, rclpy
import telemetry_monitor
telemetry_monitor.curses.curs_set = lambda *a: None
rclpy.init()
node = telemetry_monitor.TelemetryMonitor()
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
start_t = time.time()
while time.time() - start_t < 90:
    rclpy.spin_once(node, timeout_sec=0.1)
    if node.drones[1] and node.drones[2]:
        lr = node.drones[1].get('latest_release')
        if lr and node.locked_release_poses.get(lr.get('package_id')) != "PENDING":
            break
stdscr = DummyStdscr()
telemetry_monitor.draw_dashboard(stdscr, node)
for y in sorted(stdscr.lines.keys()):
    row = stdscr.lines[y]
    line = ""
    for x in sorted(row.keys()):
        line += " " * (x - len(line)) + str(row[x])
    print(line)
node.destroy_node()
rclpy.shutdown()
