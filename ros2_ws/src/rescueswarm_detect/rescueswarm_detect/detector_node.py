import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO

class Detector(Node):
    def __init__(self):
        super().__init__('detector_node')
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        self.bridge = CvBridge()
        self.get_logger().info('Loading YOLO model...')
        self.model = YOLO('yolov8n.pt')
        self.get_logger().info('Model loaded. Subscribing to camera...')
        self.sub = self.create_subscription(Image, '/x500_claw/camera', self.cb, qos)
        self.frame_count = 0

    def cb(self, msg):
        self.frame_count += 1
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        results = self.model(frame, verbose=False)
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                self.get_logger().info(f'Detection: class={cls_id} conf={conf:.2f}')
        if self.frame_count % 50 == 0:
            self.get_logger().info(f'Processed {self.frame_count} frames so far')

def main():
    rclpy.init()
    node = Detector()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
