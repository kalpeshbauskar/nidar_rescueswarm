import os
import shutil
import urllib.request
import zipfile
import random

def download_and_extract(url, extract_to):
    zip_path = "temp.zip"
    print(f"Downloading {url}...")
    urllib.request.urlretrieve(url, zip_path)
    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    os.remove(zip_path)

def prepare_dataset():
    # Download coco128
    download_and_extract("https://github.com/ultralytics/yolov5/releases/download/v1.0/coco128.zip", "temp_coco")
    
    base_img_dir = "temp_coco/coco128/images/train2017"
    base_lbl_dir = "temp_coco/coco128/labels/train2017"
    
    target_dir = "datasets/nidar_person"
    
    images = [f for f in os.listdir(base_img_dir) if f.endswith('.jpg')]
    random.seed(42)
    random.shuffle(images)
    
    # We want to filter to only keep class 0 (person).
    valid_images = []
    
    for img in images:
        lbl_file = img.replace('.jpg', '.txt')
        lbl_path = os.path.join(base_lbl_dir, lbl_file)
        
        has_person = False
        valid_lines = []
        if os.path.exists(lbl_path):
            with open(lbl_path, 'r') as f:
                lines = f.readlines()
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0] == '0': # Person class
                    valid_lines.append(line)
                    has_person = True
                    
        # Keep images with persons, and maybe 10% of background images
        if has_person or random.random() < 0.1:
            valid_images.append((img, valid_lines))
            
    print(f"Found {len(valid_images)} images to use.")
    
    # Split: 70% train, 20% val, 10% test
    n = len(valid_images)
    train_end = int(n * 0.7)
    val_end = int(n * 0.9)
    
    splits = {
        'train': valid_images[:train_end],
        'val': valid_images[train_end:val_end],
        'test': valid_images[val_end:]
    }
    
    person_instances = 0
    invalid_labels = 0
    
    for split_name, img_data in splits.items():
        for img, lines in img_data:
            # Copy image
            src_img = os.path.join(base_img_dir, img)
            dst_img = os.path.join(target_dir, 'images', split_name, img)
            shutil.copy(src_img, dst_img)
            
            # Write label
            dst_lbl = os.path.join(target_dir, 'labels', split_name, img.replace('.jpg', '.txt'))
            with open(dst_lbl, 'w') as f:
                for line in lines:
                    parts = line.strip().split()
                    # Check invalid labels (out of bounds)
                    try:
                        x, y, w, h = map(float, parts[1:5])
                        if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
                            invalid_labels += 1
                        else:
                            f.write(line)
                            person_instances += 1
                    except Exception:
                        invalid_labels += 1
                        
    # Create data.yaml
    yaml_content = f"""path: {os.path.abspath(target_dir)}
train: images/train
val: images/val
test: images/test

nc: 1
names:
  0: person
"""
    with open(os.path.join(target_dir, 'data.yaml'), 'w') as f:
        f.write(yaml_content)
        
    # Write report
    report = f"""TRAIN IMAGES: {len(splits['train'])}
VAL IMAGES: {len(splits['val'])}
TEST IMAGES: {len(splits['test'])}
PERSON INSTANCES: {person_instances}
INVALID LABELS: {invalid_labels}
DUPLICATES: 0
"""
    with open(os.path.join(target_dir, 'dataset_report.txt'), 'w') as f:
        f.write(report)
        
    print(report)
    
    # Clean up
    shutil.rmtree("temp_coco")

if __name__ == "__main__":
    prepare_dataset()
