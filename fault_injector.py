import json
import time

def inject_fault(drone_id, wifi=True, rfd=True, nav=True):
    faults = {}
    try:
        with open("faults.json", "r") as f:
            faults = json.load(f)
    except:
        pass
    faults[str(drone_id)] = {"wifi": wifi, "rfd": rfd, "nav": nav}
    with open("faults.json", "w") as f:
        json.dump(faults, f)

if __name__ == "__main__":
    import sys
    drone_id = int(sys.argv[1])
    wifi = sys.argv[2].lower() == "true"
    rfd = sys.argv[3].lower() == "true"
    nav = sys.argv[4].lower() == "true"
    inject_fault(drone_id, wifi, rfd, nav)
    print(f"Injected for drone {drone_id}: wifi={wifi}, rfd={rfd}, nav={nav}")
