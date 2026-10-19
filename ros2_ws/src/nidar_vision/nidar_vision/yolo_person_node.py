import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from cv_bridge import CvBridge
import cv2
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../../venv/lib/python3.12/site-packages'))
try:
    import torch
    from ultralytics import YOLO
except ImportError:
    sys.path.insert(0, '/home/kalpeshbauskar/nidar_rescueswarm/venv/lib/python3.12/site-packages')
    import torch
    from ultralytics import YOLO


class YoloPersonNode(Node):
    def __init__(self):
        super().__init__('yolo_person_node')
        
        self.declare_parameter('model_path', 'yolov8n.pt') # yolo11n.pt if using YOLO11
        self.declare_parameter('confidence_threshold', 0.40)
        self.declare_parameter('iou_threshold', 0.45)
        self.declare_parameter('device', 'cpu') # Use CUDA if available
        self.declare_parameter('image_topic', '/nidar/camera/image_raw')
        self.declare_parameter('annotated_image_topic', '/nidar/yolo/image_annotated')
        self.declare_parameter('detections_topic', '/nidar/yolo/detections')
        
        model_path = self.get_parameter('model_path').value
        self.conf_thres = self.get_parameter('confidence_threshold').value
        self.iou_thres = self.get_parameter('iou_threshold').value
        device_str = self.get_parameter('device').value
        
        image_topic = self.get_parameter('image_topic').value
        annotated_image_topic = self.get_parameter('annotated_image_topic').value
        detections_topic = self.get_parameter('detections_topic').value
        
        self.get_logger().info(f'Loading YOLO model from {model_path} on {device_str}')
        self.model = YOLO(model_path)
        # Removed .to(device_str) because it fails for ONNX models
        
        self.bridge = CvBridge()
        
        from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
        
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        self.subscription = self.create_subscription(
            Image,
            image_topic,
            self.image_callback,
            qos_profile)
            
        self.annotated_pub = self.create_publisher(Image, annotated_image_topic, 1)
        self.detections_pub = self.create_publisher(Detection2DArray, detections_topic, 1)
        
        self.get_logger().info('YOLO Person Node Initialized.')
        self.is_processing = False

    def image_callback(self, msg):
        if self.is_processing:
            # Drop frame to prevent backlog
            return
            
        self.is_processing = True
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed to convert image: {e}')
            self.is_processing = False
            return

            
        results = self.model.predict(
            source=cv_image, 
            conf=self.conf_thres, 
            iou=self.iou_thres, 
            classes=[0], # Person class in COCO
            verbose=False
        )
        
        detections_msg = Detection2DArray()
        detections_msg.header = msg.header
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Bounding box coordinates
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                det = Detection2D()
                det.header = msg.header
                
                # Center and size
                det.bbox.center.position.x = float((x1 + x2) / 2)
                det.bbox.center.position.y = float((y1 + y2) / 2)
                det.bbox.size_x = float(x2 - x1)
                det.bbox.size_y = float(y2 - y1)
                
                hyp = ObjectHypothesisWithPose()
                hyp.hypothesis.class_id = str(cls)
                hyp.hypothesis.score = conf
                det.results.append(hyp)
                
                detections_msg.detections.append(det)
        
        self.detections_pub.publish(detections_msg)
        
        # Publish annotated image
        annotated_frame = results[0].plot()
        annotated_msg = self.bridge.cv2_to_imgmsg(annotated_frame, encoding="bgr8")
        annotated_msg.header = msg.header
        self.annotated_pub.publish(annotated_msg)
            
        self.is_processing = False

def main(args=None):
    rclpy.init(args=args)
    node = YoloPersonNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
