with open("mission.py", "r") as f:
    lines = f.readlines()
for i in range(len(lines)):
    if "self.csv.writerow([" in lines[i]:
        if i < 200:
            lines[i] = "        self.csv.writerow([\n"
        else:
            lines[i] = "                self.csv.writerow([\n"
with open("mission.py", "w") as f:
    f.writelines(lines)
