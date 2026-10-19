import os
import torch
from ultralytics import YOLO

def train_yolo():
    # Use GPU if available
    device = '0' if torch.cuda.is_available() else 'cpu'
    
    # Pretrained lightweight model as starting point
    model = YOLO('yolo11n.pt')
    
    data_yaml = os.path.abspath(os.path.join(os.path.dirname(__file__), '../datasets/nidar_person/data.yaml'))
    
    # Train
    results = model.train(
        data=data_yaml,
        epochs=50, # Initial quick run
        imgsz=640,
        batch=16, # or 'auto' (but 16 is safe for Nano/CPU)
        device=device,
        workers=4,
        patience=10, # early stopping
        # Augmentations suitable for aerial/rescue:
        degrees=10.0,
        translate=0.1,
        scale=0.2, # slight scaling
        fliplr=0.5,
        mosaic=0.5, # moderate mosaic
        project='runs/detect',
        name='person_training',
        exist_ok=True
    )
    
    print("Training Complete.")
    print("Metrics:")
    # Print metrics from results
    print(f"mAP50: {results.box.map50}")
    print(f"mAP50-95: {results.box.map}")
    print(f"Precision: {results.box.mp}")
    print(f"Recall: {results.box.mr}")

if __name__ == "__main__":
    train_yolo()
