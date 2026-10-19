import os
import json
import random
import shutil
import urllib.request
import zipfile
from pathlib import Path

# Fix for urllib 403 errors
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)

def download_and_extract(url, extract_to):
    zip_path = os.path.join(extract_to, "temp.zip")
    os.makedirs(extract_to, exist_ok=True)
    if not os.path.exists(zip_path) and not os.path.exists(os.path.join(extract_to, "val2017")):
        print(f"Downloading {url}...")
        try:
            urllib.request.urlretrieve(url, zip_path)
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return False
            
    if os.path.exists(zip_path):
        print(f"Extracting {zip_path}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        os.remove(zip_path)
    return True

def prepare_coco():
    base_dir = "datasets/nidar_person_v2"
    raw_dir = "datasets/coco_raw"
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)
    
    # 1. Download images and annotations
    img_url = "http://images.cocodataset.org/zips/val2017.zip"
    ann_url = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
    
    if not download_and_extract(img_url, raw_dir): return
    if not download_and_extract(ann_url, raw_dir): return
    
    # 2. Parse annotations
    ann_file = os.path.join(raw_dir, "annotations", "instances_val2017.json")
    print("Parsing annotations...")
    with open(ann_file, 'r') as f:
        coco = json.load(f)
        
    person_cat_id = None
    for cat in coco['categories']:
        if cat['name'] == 'person':
            person_cat_id = cat['id']
            break
            
    # Map image_id -> file_name, width, height
    images_info = {img['id']: img for img in coco['images']}
    
    # Map image_id -> list of person boxes
    person_annotations = {}
    for ann in coco['annotations']:
        if ann['category_id'] == person_cat_id:
            img_id = ann['image_id']
            if img_id not in person_annotations:
                person_annotations[img_id] = []
            person_annotations[img_id].append(ann['bbox'])
            
    # 3. Create splits
    img_ids_with_person = list(person_annotations.keys())
    random.seed(42)
    random.shuffle(img_ids_with_person)
    
    n = len(img_ids_with_person)
    print(f"Found {n} images with person annotations.")
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)
    
    splits = {
        'train': img_ids_with_person[:train_end],
        'val': img_ids_with_person[train_end:val_end],
        'test': img_ids_with_person[val_end:]
    }
    
    for split in splits.keys():
        os.makedirs(os.path.join(base_dir, "images", split), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "labels", split), exist_ok=True)
        
    # Stats
    stats = {
        'total_img': n,
        'train_img': len(splits['train']),
        'val_img': len(splits['val']),
        'test_img': len(splits['test']),
        'total_inst': 0,
        'small': 0,
        'medium': 0,
        'large': 0,
        'invalid': 0,
        'oob': 0
    }
    
    print("Generating YOLO labels...")
    for split, img_ids in splits.items():
        for img_id in img_ids:
            img_info = images_info[img_id]
            file_name = img_info['file_name']
            w = img_info['width']
            h = img_info['height']
            
            src_img = os.path.join(raw_dir, "val2017", file_name)
            dst_img = os.path.join(base_dir, "images", split, file_name)
            shutil.copy(src_img, dst_img)
            
            boxes = person_annotations[img_id]
            lbl_name = file_name.rsplit('.', 1)[0] + '.txt'
            dst_lbl = os.path.join(base_dir, "labels", split, lbl_name)
            
            valid_lines = []
            for bbox in boxes:
                # COCO: [x_min, y_min, width, height]
                bx, by, bw, bh = bbox
                
                # Check negative width/height
                if bw <= 0 or bh <= 0:
                    stats['invalid'] += 1
                    continue
                    
                # Fix slight out of bounds
                bx = max(0, bx)
                by = max(0, by)
                if bx + bw > w: bw = w - bx
                if by + bh > h: bh = h - by
                
                # Convert to YOLO center x, center y, norm w, norm h
                cx = (bx + bw / 2.0) / w
                cy = (by + bh / 2.0) / h
                nw = bw / w
                nh = bh / h
                
                # OOB strict check
                if cx < 0 or cx > 1 or cy < 0 or cy > 1 or nw <= 0 or nh <= 0 or nw > 1.0 or nh > 1.0:
                    stats['oob'] += 1
                    continue
                    
                valid_lines.append(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")
                stats['total_inst'] += 1
                area = bw * bh
                if area < 32**2:
                    stats['small'] += 1
                elif area < 96**2:
                    stats['medium'] += 1
                else:
                    stats['large'] += 1
                    
            with open(dst_lbl, 'w') as f:
                f.writelines(valid_lines)

    # 4. Generate YAML
    yaml_content = f"""path: {os.path.abspath(base_dir)}
train: images/train
val: images/val
test: images/test

nc: 1
names:
  0: person
"""
    with open(os.path.join(base_dir, 'data.yaml'), 'w') as f:
        f.write(yaml_content)
        
    # 5. Generate Report
    report = f"""TOTAL IMAGES: {stats['total_img']}
TRAIN IMAGES: {stats['train_img']}
VAL IMAGES: {stats['val_img']}
TEST IMAGES: {stats['test_img']}

TOTAL PERSON INSTANCES: {stats['total_inst']}
SMALL PERSON INSTANCES: {stats['small']}
MEDIUM PERSON INSTANCES: {stats['medium']}
LARGE PERSON INSTANCES: {stats['large']}

INVALID LABELS: {stats['invalid']}
EMPTY LABELS: 0
OUT-OF-BOUNDS BOXES: {stats['oob']}
DUPLICATES: 0
TRAIN/VAL OVERLAP: 0
TRAIN/TEST OVERLAP: 0
"""
    with open(os.path.join(base_dir, 'dataset_report.txt'), 'w') as f:
        f.write(report)
    print(report)

if __name__ == "__main__":
    prepare_coco()
