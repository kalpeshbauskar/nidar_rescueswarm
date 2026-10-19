with open("mission.py", "r") as f:
    data = f.read()

bad = """                if self.target_n is not None:
                    target_n, target_e, target_alt = self.target_n, self.target_e, -self.target_d"""

good = """                if hasattr(self, 'target') and self.target is not None:
                    target_n, target_e, target_alt = self.target[0], self.target[1], -self.target[2]"""

data = data.replace(bad, good)
with open("mission.py", "w") as f:
    f.write(data)
