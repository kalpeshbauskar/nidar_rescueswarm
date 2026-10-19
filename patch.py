import re
with open("simulation/dual/mission.py", "r") as f:
    c = f.read()
c = c.replace(
    "if now - self.start > 90:",
    "if now - self.start > 90:\n                print(f'Missing: global_p={self.global_p is not None}, s={self.s is not None}, p={self.p is not None}, xy_valid={self.p.xy_valid if self.p else False}, z_valid={self.p.z_valid if self.p else False}, att={self.att is not None}, frames={self.frames}', flush=True)"
)
with open("simulation/dual/mission.py", "w") as f:
    f.write(c)
