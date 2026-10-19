import os
import shutil
import time
from ultralytics import YOLO
import torch

def export_model():
    best_pt_path = '../runs/detect/runs/detect/person_training/weights/best.pt'
    models_dir = '../models'
    
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
        
    print(f"Loading {best_pt_path}...")
    model = YOLO(best_pt_path)
    
    # Save best.pt
    dest_pt = os.path.join(models_dir, 'person_best.pt')
    shutil.copy(best_pt_path, dest_pt)
    print(f"Saved PyTorch model to {dest_pt}")
    
    # Export ONNX
    print("Exporting ONNX...")
    # ONNX export format
    model.export(format='onnx', imgsz=640)
    
    # Ultralytics saves the exported file next to the original best.pt
    onnx_path = best_pt_path.replace('.pt', '.onnx')
    dest_onnx = os.path.join(models_dir, 'person_best.onnx')
    if os.path.exists(onnx_path):
        shutil.copy(onnx_path, dest_onnx)
        print(f"Saved ONNX model to {dest_onnx}")
    else:
        print("ONNX export failed or file not found.")

    # Optionally attempt TensorRT export
    # This requires TensorRT installed on the host. Since we don't know, we use a try-except
    print("Exporting TensorRT (if available)...")
    try:
        model.export(format='engine', imgsz=640, device='0')
        engine_path = best_pt_path.replace('.pt', '.engine')
        dest_engine = os.path.join(models_dir, 'person_best.engine')
        if os.path.exists(engine_path):
            shutil.copy(engine_path, dest_engine)
            print(f"Saved TensorRT model to {dest_engine}")
    except Exception as e:
        print(f"TensorRT export skipped or failed: {e}")

    # Benchmark PyTorch
    print("Benchmarking PyTorch model...")
    t0 = time.time()
    res = model.predict(torch.zeros((1, 3, 640, 640)), verbose=False)
    t1 = time.time()
    pytorch_fps = 1.0 / (t1 - t0)
    print(f"PyTorch FPS (Batch 1, 640x640): {pytorch_fps:.2f} (Latency: {(t1-t0)*1000:.2f} ms)")
    
    # Benchmark ONNX
    if os.path.exists(dest_onnx):
        try:
            onnx_model = YOLO(dest_onnx)
            print("Benchmarking ONNX model...")
            import numpy as np
            import cv2
            dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
            t0 = time.time()
            res = onnx_model.predict(dummy_img, verbose=False)
            t1 = time.time()
            onnx_fps = 1.0 / (t1 - t0)
            print(f"ONNX FPS: {onnx_fps:.2f} (Latency: {(t1-t0)*1000:.2f} ms)")
        except Exception as e:
            print(f"Could not benchmark ONNX: {e}")

if __name__ == "__main__":
    export_model()
