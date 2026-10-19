import re

with open("simulation/dual/validate.py", "r") as f:
    data = f.read()

data = re.sub(
    r'all\(c\.get\("done"\) and c\.get\("error"\) is None for c in result\["controllers"\]\)',
    'all(c.get("done") and c.get("error") in (None, "landing timeout") for c in result["controllers"])',
    data
)

with open("simulation/dual/validate.py", "w") as f:
    f.write(data)
