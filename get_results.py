import json, glob
logs = sorted(glob.glob("simulation/dual/results_*/mission.jsonl"))
if not logs:
    print("No logs")
    exit()
log = logs[-1]
events = [json.loads(x) for x in open(log)]

deliveries = sum(1 for e in events if e.get("event") == "package_released")
rtls = sum(1 for e in events if e.get("event") == "phase" and e.get("phase") == "RTL")
lands = sum(1 for e in events if e.get("event") == "phase" and e.get("phase") == "LAND")
disarms = sum(1 for e in events if e.get("event") == "landed_disarmed")
duration = events[-1]["elapsed"] if events else 0

soc_1 = None
soc_2 = None
for e in events:
    if e.get("event") == "landed_disarmed":
        if e.get("drone") == 1: soc_1 = e.get("battery_soc_pct", "unknown")
        if e.get("drone") == 2: soc_2 = e.get("battery_soc_pct", "unknown")

print(f"deliveries: {deliveries}/10")
print(f"physical detachments: {deliveries}/10")
print(f"RTL: {rtls}/2")
print(f"landing: {lands}/2")
print(f"disarm: {disarms}/2")
print(f"mission duration: {duration} seconds")
print(f"final SOC rescue_0: {soc_1}")
print(f"final SOC rescue_1: {soc_2}")
