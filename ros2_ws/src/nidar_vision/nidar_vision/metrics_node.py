import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray
import time

class MetricsNode(Node):
    def __init__(self):
        super().__init__('metrics_node')
        
        self.cam_count = 0
        self.yolo_count = 0
        self.annotated_count = 0
        self.start_time = time.time()
        
        self.create_subscription(Image, '/nidar/camera/image_raw', self.cam_cb, 10)
        self.create_subscription(Detection2DArray, '/nidar/yolo/detections', self.yolo_cb, 10)
        self.create_subscription(Image, '/nidar/yolo/image_annotated', self.annotated_cb, 10)
        
        self.timer = self.create_timer(5.0, self.report_metrics)
        
    def cam_cb(self, msg):
        self.cam_count += 1
        
    def yolo_cb(self, msg):
        self.yolo_count += 1
        
    def annotated_cb(self, msg):
        self.annotated_count += 1
        
    def report_metrics(self):
        elapsed = time.time() - self.start_time
        if elapsed < 1:
            return
            
        cam_fps = self.cam_count / elapsed
        yolo_fps = self.yolo_count / elapsed
        annotated_fps = self.annotated_count / elapsed
        
        self.get_logger().info('--- Performance Metrics ---')
        self.get_logger().info(f'Camera FPS: {cam_fps:.2f}')
        self.get_logger().info(f'YOLO Inference FPS: {yolo_fps:.2f}')
        self.get_logger().info(f'Annotated Image FPS: {annotated_fps:.2f}')
        
        # Reset counters
        self.cam_count = 0
        self.yolo_count = 0
        self.annotated_count = 0
        self.start_time = time.time()

def main(args=None):
    rclpy.init(args=args)
    node = MetricsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
