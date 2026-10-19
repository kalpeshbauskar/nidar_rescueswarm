import os
import sys
import time
import shutil
from ultralytics import YOLO

def train():
    data_yaml = os.path.abspath(os.path.join(os.path.dirname(__file__), '../datasets/nidar_person_v2/data.yaml'))
    
    # Allowed optimization: 512 for training
    model = YOLO('yolo11n.pt')
    
    # We will wrap the train call or just rely on ultralytics printing
    print("Starting YOLO training on CPU...")
    # Because it's CPU, we use a small batch size or 'auto'. 16 is fine.
    
    start_time = time.time()
    
    results = model.train(
        data=data_yaml,
        epochs=50,
        imgsz=512,
        batch=16,
        device='cpu',
        workers=4,
        patience=8,
        single_cls=True,
        cache=True,  # Cache labels/images in RAM
        project='runs/detect',
        name='person_v2',
        exist_ok=True
    )
    
    end_time = time.time()
    print(f"Training completed in {(end_time - start_time) / 60:.2f} minutes.")
    
    # Validate at 640
    print("Validating at imgsz=640...")
    val_results = model.val(imgsz=640)
    
    # Export
    print("Exporting to ONNX...")
    try:
        exported_path = model.export(format='onnx', dynamic=True, simplify=True)
        dest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models/person_best.onnx'))
        
        # Copy the ONNX to the expected models directory
        if os.path.exists(exported_path):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy(exported_path, dest_path)
            print(f"Moved ONNX to {dest_path}")
            
    except Exception as e:
        print(f"Export ONNX failed: {e}")
        
    print("TENSORRT EXPORT BYPASSED: TO BE GENERATED ON JETSON ORIN NANO")
    print("DONE TRAINING")

if __name__ == "__main__":
    train()
