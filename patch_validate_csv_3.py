with open("simulation/dual/validate.py", "r") as f:
    data = f.read()

replacement = """            # Ground reached (alt < 0.5m), stable (roll/pitch < 30 deg ~ 0.5 rad)
            nav_state = int(last_line[7])
            armed = int(last_line[6])
            
            # Nav state 18 is Auto-Land (which transitions to ground contact)
            if altitude < 0.5 and abs(roll) < 0.5 and abs(pitch) < 0.5 and nav_state == 18:
                return True"""

data = data.replace('            # Ground reached (alt < 0.5m), stable (roll/pitch < 30 deg ~ 0.5 rad)\n            if altitude < 0.5 and abs(roll) < 0.5 and abs(pitch) < 0.5:\n                return True', replacement)

with open("simulation/dual/validate.py", "w") as f:
    f.write(data)
