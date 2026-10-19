import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from cv_bridge import CvBridge
import cv2
import numpy as np
import math
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../../venv/lib/python3.12/site-packages'))
try:
    import torch
    import torchvision
    from torchvision.models.detection import ssdlite320_mobilenet_v3_large, SSDLite320_MobileNet_V3_Large_Weights
except ImportError:
    sys.path.insert(0, '/home/kalpeshbauskar/nidar_rescueswarm/venv/lib/python3.12/site-packages')
    import torch
    import torchvision
    from torchvision.models.detection import ssdlite320_mobilenet_v3_large, SSDLite320_MobileNet_V3_Large_Weights


class SsdPersonNode(Node):
    """
    SSD (Single Shot MultiBox Detector) Person Detection Node
    Utilizes MobileNetV3-Large SSDLite (COCO pretrained) for real-time person detection.
    """
    def __init__(self):
        super().__init__('ssd_person_node')
        
        self.declare_parameter('confidence_threshold', 0.35)
        self.declare_parameter('iou_threshold', 0.45)
        self.declare_parameter('device', 'cpu')
        self.declare_parameter('image_topic', '/nidar/camera/image_raw')
        self.declare_parameter('annotated_image_topic', '/nidar/ssd/image_annotated')
        self.declare_parameter('detections_topic', '/nidar/ssd/detections')
        
        self.conf_thres = self.get_parameter('confidence_threshold').value
        self.iou_thres = self.get_parameter('iou_threshold').value
        device_str = self.get_parameter('device').value
        
        if (device_str in ['cuda', 'auto']) and torch.cuda.is_available():
            self.device = torch.device('cuda')
        else:
            self.device = torch.device('cpu')
            try:
                torch.set_num_threads(2)
            except Exception:
                pass
            
        image_topic = self.get_parameter('image_topic').value
        annotated_image_topic = self.get_parameter('annotated_image_topic').value
        detections_topic = self.get_parameter('detections_topic').value
        
        self.get_logger().info(f'Loading SSD (SSDLite320-MobileNetV3) model on device {self.device}')
        try:
            weights = SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
            self.model = ssdlite320_mobilenet_v3_large(weights=weights)
        except Exception as e:
            self.get_logger().warn(f'Default weights load fallback: {e}')
            cache_file = os.path.expanduser('~/.cache/torch/hub/checkpoints/ssdlite320_mobilenet_v3_large_coco-a79551df.pth')
            local_file = os.path.join(os.path.dirname(__file__), '../../../../models/ssd/ssdlite320_mobilenet_v3_large_coco.pth')
            load_path = cache_file if os.path.exists(cache_file) else local_file
            self.model = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
            self.model.load_state_dict(torch.load(load_path, map_location=self.device))

        self.model.to(self.device)
        self.model.eval()
        
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
            qos_profile
        )
        
        self.annotated_pub = self.create_publisher(Image, annotated_image_topic, 1)
        self.detections_pub = self.create_publisher(Detection2DArray, detections_topic, 1)

        # Dual publishing for seamless backward compatibility
        self.compat_annotated_pub = self.create_publisher(
            Image, annotated_image_topic.replace('/ssd/', '/yolo/'), 1
        ) if '/ssd/' in annotated_image_topic else None

        self.compat_detections_pub = self.create_publisher(
            Detection2DArray, detections_topic.replace('/ssd/', '/yolo/'), 1
        ) if '/ssd/' in detections_topic else None
        
        self.is_processing = False
        self.fps_time = time.monotonic()
        self.fps = 0.0
        self.get_logger().info(f'SSD Person Node Initialized. Subscribed: {image_topic}, Publishing detections: {detections_topic}')

    def image_callback(self, msg):
        if self.is_processing:
            return
            
        self.is_processing = True
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed to convert image in SSD node: {e}')
            self.is_processing = False
            return
            
        t_start = time.monotonic()
        h, w = cv_image.shape[:2]
        
        # Preprocessing: convert BGR to RGB and normalize tensor to [0, 1]
        rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0).to(self.device)
        
        with torch.no_grad():
            output = self.model([tensor])[0]
            
        boxes = output['boxes'].detach().cpu().numpy()
        scores = output['scores'].detach().cpu().numpy()
        labels = output['labels'].detach().cpu().numpy()
        
        detections_msg = Detection2DArray()
        detections_msg.header = msg.header
        
        annotated_frame = cv_image.copy()
        person_count = 0
        
        # Label 1 is 'person' in COCO SSDLite
        for box, score, label in zip(boxes, scores, labels):
            if label == 1 and score >= self.conf_thres:
                x1, y1, x2, y2 = box.tolist()
                bw = max(0.0, x2 - x1)
                bh = max(0.0, y2 - y1)
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                
                # Edge exclusion: filter detections too close to image borders
                if cx < 35 or cx > w - 35 or cy < 30 or cy > h - 30:
                    continue

                det = Detection2D()
                det.header = msg.header
                det.bbox.center.position.x = float(cx)
                det.bbox.center.position.y = float(cy)
                det.bbox.size_x = float(bw)
                det.bbox.size_y = float(bh)
                
                hyp = ObjectHypothesisWithPose()
                hyp.hypothesis.class_id = '0'  # 0 indicates person to match mission conventions
                hyp.hypothesis.score = float(score)
                det.results.append(hyp)
                
                detections_msg.detections.append(det)
                person_count += 1
                
                # Visual annotation
                ix1, iy1, ix2, iy2 = int(x1), int(y1), int(x2), int(y2)
                cv2.rectangle(annotated_frame, (ix1, iy1), (ix2, iy2), (0, 255, 0), 2)
                label_text = f"SSD Person: {score * 100:.1f}%"
                cv2.rectangle(annotated_frame, (ix1, max(0, iy1 - 20)), (ix1 + 180, iy1), (0, 180, 0), -1)
                cv2.putText(annotated_frame, label_text, (ix1 + 4, max(14, iy1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # SAR Aerial Survivor Detection (High-visibility orange SOLAS rescue vest on flood debris)
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        orange_mask = cv2.inRange(hsv, np.array([5, 120, 90]), np.array([28, 255, 255]))
        # Mask out 35px borders to completely ignore drone landing gear / frame edges
        orange_mask[:35, :] = 0
        orange_mask[-35:, :] = 0
        orange_mask[:, :35] = 0
        orange_mask[:, -35:] = 0

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        orange_mask = cv2.morphologyEx(orange_mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(orange_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 10 <= area <= 4000:
                M = cv2.moments(cnt)
                if M['m00'] > 0:
                    cx = float(M['m10'] / M['m00'])
                    cy = float(M['m01'] / M['m00'])
                    rx, ry, rw, rh = cv2.boundingRect(cnt)

                    # Check if already covered by an SSD box
                    already_covered = False
                    for existing_det in detections_msg.detections:
                        ecx = existing_det.bbox.center.position.x
                        ecy = existing_det.bbox.center.position.y
                        if math.hypot(cx - ecx, cy - ecy) < 35.0:
                            already_covered = True
                            break

                    if not already_covered:
                        det = Detection2D()
                        det.header = msg.header
                        det.bbox.center.position.x = float(cx)
                        det.bbox.center.position.y = float(cy)
                        det.bbox.size_x = float(max(rw, 22.0))
                        det.bbox.size_y = float(max(rh, 22.0))

                        hyp = ObjectHypothesisWithPose()
                        hyp.hypothesis.class_id = '0'  # person class
                        hyp.hypothesis.score = 0.95
                        det.results.append(hyp)

                        detections_msg.detections.append(det)
                        person_count += 1

                        # Visual annotation for SAR detection
                        cv2.rectangle(annotated_frame, (rx, ry), (rx + rw, ry + rh), (0, 140, 255), 2)
                        label_text = "SAR Survivor: 95.0%"
                        cv2.rectangle(annotated_frame, (rx, max(0, ry - 20)), (rx + 175, ry), (0, 140, 255), -1)
                        cv2.putText(annotated_frame, label_text, (rx + 4, max(14, ry - 5)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        self.detections_pub.publish(detections_msg)
        if self.compat_detections_pub is not None:
            self.compat_detections_pub.publish(detections_msg)

        # Calculate inference FPS
        dt = time.monotonic() - t_start
        if dt > 0:
            inst_fps = 1.0 / dt
            self.fps = 0.8 * self.fps + 0.2 * inst_fps

        # Draw HUD status overlay
        hud_text = f"[SSD+SAR SwarmVision] FPS: {self.fps:.1f} | Detections: {person_count}"
        cv2.putText(annotated_frame, hud_text, (10, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
                    
        annotated_msg = self.bridge.cv2_to_imgmsg(annotated_frame, encoding="bgr8")
        annotated_msg.header = msg.header
        self.annotated_pub.publish(annotated_msg)
        if self.compat_annotated_pub is not None:
            self.compat_annotated_pub.publish(annotated_msg)
        
        self.is_processing = False


def main(args=None):
    rclpy.init(args=args)
    node = SsdPersonNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
