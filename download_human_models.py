import os
import urllib.request
import json
import urllib.parse

base_dir = "simulation/imported/humans"
os.makedirs(base_dir, exist_ok=True)

models = {
    "Standing person": "https://fuel.gazebosim.org/1.0/OpenRobotics/models/Standing%20person",
    "Walking person": "https://fuel.gazebosim.org/1.0/OpenRobotics/models/Walking%20person",
    "Casual female": "https://fuel.gazebosim.org/1.0/OpenRobotics/models/Casual%20female"
}

opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)

def extract_paths(node, paths):
    if "children" in node:
        for child in node["children"]:
            extract_paths(child, paths)
    elif "path" in node:
        paths.append(node["path"])

for name, url in models.items():
    print(f"Downloading {name}...")
    model_dir = os.path.join(base_dir, name.replace(" ", "_"))
    os.makedirs(model_dir, exist_ok=True)
    
    files_url = f"{url}/1/files"
    try:
        response = urllib.request.urlopen(files_url)
        files_data = json.loads(response.read().decode('utf-8'))
        
        paths = []
        for root_node in files_data.get("file_tree", []):
            extract_paths(root_node, paths)
            
        for path in paths:
            if not path or "/thumbnails/" in path:
                continue
            
            # Create local directories
            local_path = os.path.join(model_dir, path.lstrip("/"))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            download_url = f"{url}/1/files{path}"
            download_url = urllib.parse.quote(download_url, safe=':/')
            print(f"  Fetching {path}...")
            try:
                urllib.request.urlretrieve(download_url, local_path)
            except Exception as e2:
                print(f"  Failed to fetch {path}: {e2}")
    except Exception as e:
        print(f"Failed to list {name}: {e}")
print("Done.")
