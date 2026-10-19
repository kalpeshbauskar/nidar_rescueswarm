import os
import sys
import time
import shutil
from ultralytics import YOLO

def train():
    data_yaml = os.path.abspath(os.path.join(os.path.dirname(__file__), '../datasets/nidar_person_v2/data.yaml'))
    
    # Continue fine-tuning from the newest checkpoint
    last_pt = os.path.abspath(os.path.join(os.path.dirname(__file__), '../runs/detect/runs/detect/person_v2/weights/last.pt'))
    if not os.path.exists(last_pt):
        print(f"Error: {last_pt} not found!")
        sys.exit(1)
        
    model = YOLO(last_pt)
    
    print("Starting YOLO training (accelerated) on CPU...")
    
    start_time = time.time()
    
    # Using the updated settings
    results = model.train(
        data=data_yaml,
        epochs=50,
        imgsz=512,
        batch=-1, # batch=auto
        device='cpu',
        workers=8,    # workers=8
        patience=8,
        single_cls=True,
        cache=True,
        project='runs/detect',
        name='person_v2_fast', # Save separately
        exist_ok=True
    )
    
    end_time = time.time()
    print(f"Training completed in {(end_time - start_time) / 60:.2f} minutes.")
    
    # Validate at 640
    print("Validating at imgsz=640...")
    val_results = model.val(imgsz=640, split='test')
    
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
