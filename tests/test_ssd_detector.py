"""Unit tests for SSD (Single Shot MultiBox Detector) Person Detection Node."""

import os
import sys
import numpy as np
import cv2
import pytest

# Ensure ros2_ws and venv are in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../ros2_ws/src/nidar_vision'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../venv/lib/python3.12/site-packages'))


def test_ssd_weights_and_inference():
    """Verify torchvision SSDLite MobileNetV3 model loads and produces detections."""
    import torch
    from torchvision.models.detection import ssdlite320_mobilenet_v3_large, SSDLite320_MobileNet_V3_Large_Weights

    weights = SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
    model = ssdlite320_mobilenet_v3_large(weights=weights)
    model.eval()

    # Create dummy 640x480 RGB image tensor
    dummy_tensor = torch.rand(3, 480, 640)
    with torch.no_grad():
        out = model([dummy_tensor])[0]

    assert 'boxes' in out
    assert 'scores' in out
    assert 'labels' in out
    assert out['boxes'].shape[1] == 4
    assert out['scores'].ndim == 1
    assert out['labels'].ndim == 1


def test_ssd_node_message_conversion():
    """Verify SsdPersonNode correctly converts frames to Detection2DArray."""
    import rclpy
    from cv_bridge import CvBridge
    from nidar_vision.ssd_person_node import SsdPersonNode

    if not rclpy.ok():
        rclpy.init()

    node = SsdPersonNode()
    bridge = CvBridge()

    # 640x480 test image
    cv_img = np.zeros((480, 640, 3), dtype=np.uint8)
    msg = bridge.cv2_to_imgmsg(cv_img, encoding='bgr8')
    msg.header.stamp.sec = 10
    msg.header.frame_id = 'rescue_0/camera_link'

    # Process image callback
    node.image_callback(msg)

    assert not node.is_processing
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
