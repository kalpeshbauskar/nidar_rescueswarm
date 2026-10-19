import os
import shutil
from ultralytics import YOLO

def evaluate():
    best_pt_path = '../runs/detect/runs/detect/person_training/weights/best.pt'
    data_yaml = os.path.abspath(os.path.join(os.path.dirname(__file__), '../datasets/nidar_person/data.yaml'))
    
    model = YOLO(best_pt_path)
    print("Evaluating on test set...")
    metrics = model.val(data=data_yaml, split='test')
    
    print("\n--- Test Set Metrics ---")
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall: {metrics.box.mr:.4f}")
    
    # We can approximate FP and FN based on precision, recall, and instances.
    # True Positives (TP) = Precision * (TP + FP)  (not directly solvable without total predictions)
    # Actually, we can get FP and FN from the confusion matrix or we can just print the matrix.
    
    print("\nRunning inference on test images to save bounding boxes...")
    test_img_dir = '../datasets/nidar_person/images/test'
    test_imgs = [os.path.join(test_img_dir, f) for f in os.listdir(test_img_dir) if f.endswith('.jpg')]
    
    out_dir = '../runs/test_inference'
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    
    for img in test_imgs:
        results = model.predict(img, save=True, project=out_dir, name='test_images', exist_ok=True, verbose=False)
        
    print(f"Saved annotated test images to {os.path.join(out_dir, 'test_images')}")
    
if __name__ == "__main__":
    evaluate()
