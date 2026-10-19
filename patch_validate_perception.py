import re

with open("simulation/dual/validate.py", "r") as f:
    data = f.read()

data = re.sub(
    r'total_drops = sum\(len\(c\.get\("drops", \[\]\)\) for c in result\["controllers"\]\)\n\s*mission_success = \(\n\s*all\(c\.get\("done"\) and c\.get\("error"\) in \(None, "landing timeout"\) for c in result\["controllers"\]\)\n\s*and total_drops == TOTAL_PACKAGES\n\s*\)',
    '''total_drops = sum(len(c.get("drops", [])) for c in result["controllers"])
        total_detections = sum(len(c.get("detections", [])) for c in result["controllers"])
        total_confirmed = sum(sum(1 for d in c.get("detections", []) if not d.get("rejected")) for c in result["controllers"])
        total_delivered = sum(sum(1 for d in c.get("detections", []) if d.get("delivered")) for c in result["controllers"])
        
        mission_success = (
            all(c.get("done") and c.get("error") in (None, "landing timeout") for c in result["controllers"])
            and total_detections >= TOTAL_PACKAGES
            and total_confirmed >= TOTAL_PACKAGES
            and total_delivered == TOTAL_PACKAGES
            and total_drops == TOTAL_PACKAGES
        )''',
    data, flags=re.MULTILINE
)

with open("simulation/dual/validate.py", "w") as f:
    f.write(data)
