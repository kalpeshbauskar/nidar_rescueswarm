import os
import urllib.request
import zipfile

opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)

raw_dir = "datasets/coco_raw"
ann_url = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
zip_path = os.path.join(raw_dir, "temp_ann.zip")

if not os.path.exists(os.path.join(raw_dir, "annotations")):
    print("Downloading annotations...")
    urllib.request.urlretrieve(ann_url, zip_path)
    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(raw_dir)
    os.remove(zip_path)
print("Done.")
