with open("simulation/dual/validate.py", "r") as f:
    data = f.read()
data = data.replace('is_safe_timeout(c, latest_dir)', 'is_safe_timeout(c, out_dir)')
with open("simulation/dual/validate.py", "w") as f:
    f.write(data)
