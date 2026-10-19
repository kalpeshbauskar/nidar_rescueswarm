import rclpy, json, time
from std_msgs.msg import String
rclpy.init()
node = rclpy.create_node('test_sub')
node.create_subscription(String, '/swarm/drone1/state', lambda m: print("D1", m.data), 10)
node.create_subscription(String, '/swarm/drone2/state', lambda m: print("D2", m.data), 10)
for i in range(50):
    rclpy.spin_once(node, timeout_sec=0.1)
node.destroy_node()
rclpy.shutdown()
