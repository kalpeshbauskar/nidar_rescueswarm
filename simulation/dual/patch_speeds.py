with open("build_world.py", "r") as f:
    data = f.read()

data = data.replace('param set-default MPC_XY_CRUISE 8', 'param set-default MPC_XY_CRUISE 10')
data = data.replace('param set-default MPC_XY_VEL_MAX 8', 'param set-default MPC_XY_VEL_MAX 10')

with open("build_world.py", "w") as f:
    f.write(data)

with open("mission.py", "r") as f:
    mdata = f.read()

speed_setter = """
    def set_speed(self, speed):
        self.send_cmd(178, 1.0, float(speed), -1.0)
"""
# inject in DroneController
mdata = mdata.replace('def set_target(self, n, e, h):', speed_setter + '\n    def set_target(self, n, e, h):')

# patch phase transitions to set speed
mdata = mdata.replace("self.phase = 'SEARCH'", "self.phase = 'SEARCH'\n                self.set_speed(5.0)")
mdata = mdata.replace("self.phase = 'TRANSIT'", "self.phase = 'TRANSIT'\n                self.set_speed(10.0)")
mdata = mdata.replace("self.phase = 'RETURN'", "self.phase = 'RETURN'\n                self.set_speed(10.0)")
mdata = mdata.replace("self.phase = 'APPROACH'", "self.phase = 'APPROACH'\n                self.set_speed(2.0)")
mdata = mdata.replace("self.phase = 'DESCEND'", "self.phase = 'DESCEND'\n                self.set_speed(1.0)")
mdata = mdata.replace("self.phase = 'ASCEND'", "self.phase = 'ASCEND'\n                self.set_speed(5.0)")
mdata = mdata.replace("self.phase = 'RESUME'", "self.phase = 'RESUME'\n                self.set_speed(10.0)")

with open("mission.py", "w") as f:
    f.write(mdata)
