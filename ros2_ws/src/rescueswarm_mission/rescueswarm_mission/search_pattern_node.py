import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand, VehicleLocalPosition

class SearchPatternNode(Node):
    def __init__(self):
        super().__init__('search_pattern_node')
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        self.offboard_mode_pub = self.create_publisher(OffboardControlMode, '/fmu/in/offboard_control_mode', qos)
        self.setpoint_pub = self.create_publisher(TrajectorySetpoint, '/fmu/in/trajectory_setpoint', qos)
        self.cmd_pub = self.create_publisher(VehicleCommand, '/fmu/in/vehicle_command', qos)

        self.waypoints = [
            (0.0, 0.0, -5.0),
            (2.0, 0.0, -5.0),
            (2.0, 2.0, -5.0),
            (0.0, 2.0, -5.0),
        ]
        self.wp_index = 0
        self.setpoint_counter = 0

        self.timer = self.create_timer(0.1, self.timer_callback)

    def timer_callback(self):
        self.publish_offboard_mode()
        if self.setpoint_counter == 10:
            self.arm()
            self.engage_offboard_mode()
        self.publish_setpoint()
        self.setpoint_counter += 1

    def publish_offboard_mode(self):
        msg = OffboardControlMode()
        msg.position = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.offboard_mode_pub.publish(msg)

    def publish_setpoint(self):
        x, y, z = self.waypoints[self.wp_index]
        msg = TrajectorySetpoint()
        msg.position = [x, y, z]
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.setpoint_pub.publish(msg)
        if self.setpoint_counter % 100 == 0 and self.setpoint_counter > 10:
            self.wp_index = (self.wp_index + 1) % len(self.waypoints)

    def arm(self):
        self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)

    def engage_offboard_mode(self):
        self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, param1=1.0, param2=6.0)

    def send_vehicle_command(self, command, param1=0.0, param2=0.0):
        msg = VehicleCommand()
        msg.param1 = param1
        msg.param2 = param2
        msg.command = command
        msg.target_system = 1
        msg.target_component = 1
        msg.source_system = 1
        msg.source_component = 1
        msg.from_external = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.cmd_pub.publish(msg)

def main():
    rclpy.init()
    node = SearchPatternNode()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
