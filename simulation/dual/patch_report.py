import re

with open("generate_report.py", "r") as f:
    data = f.read()

csv_block = """    if csv_file.exists():
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            last_n, last_e = None, None
            for row in reader:
                try:
                    n, e = float(row.get('north', 0)), float(row.get('east', 0))
                    if last_n is not None:
                        dist += math.hypot(n - last_n, e - last_e)
                    last_n, last_e = n, e
                    
                    try:
                        alt_err = abs(float(row.get('alt_err', 'N/A')))
                        if alt_err > max_alt_err: max_alt_err = alt_err
                    except ValueError: pass
                    
                    try:
                        roll = abs(math.degrees(float(row.get('roll', 'N/A'))))
                        if roll > max_roll: max_roll = roll
                    except ValueError: pass
                    
                    try:
                        pitch = abs(math.degrees(float(row.get('pitch', 'N/A'))))
                        if pitch > max_pitch: max_pitch = pitch
                    except ValueError: pass
                    
                    try:
                        pos_err_h = float(row.get('pos_err_h', 'N/A'))
                        if pos_err_h > max_pos_err_h: max_pos_err_h = pos_err_h
                        sum_sq_pos_err_h += pos_err_h ** 2
                        pos_err_count += 1
                    except ValueError: pass
                    
                    try:
                        throttle = float(row.get('throttle', 'N/A'))
                        if throttle > max_throttle: max_throttle = throttle
                    except ValueError: pass
                except Exception as ex:
                    pass
    
    rms_pos_err_h = math.sqrt(sum_sq_pos_err_h / pos_err_count) if pos_err_count > 0 else 0.0"""

# We need to inject initializers for these new max variables
init_block = """    dist = 0
    max_alt_err = 0
    max_roll = 0
    max_pitch = 0
    max_pos_err_h = 0
    sum_sq_pos_err_h = 0
    pos_err_count = 0
    max_throttle = 0"""

data = re.sub(r'    dist = 0\s+max_alt_err = 0\s+max_roll = 0\s+max_pitch = 0', init_block, data)
data = re.sub(r'    if csv_file\.exists\(\):.*?(?=\n\n    hw = stat\.get)', csv_block, data, flags=re.DOTALL)

metric_block = """        "Maximum altitude error": f"{max_alt_err:.2f} m",
        "Maximum position error": f"{max_pos_err_h:.2f} m",
        "RMS position error": f"{rms_pos_err_h:.2f} m",
        "Maximum roll": f"{max_roll:.1f} deg",
        "Maximum pitch": f"{max_pitch:.1f} deg",
        "Maximum throttle": f"{max_throttle:.2f}",
        "Physical releases": deliv,"""
        
data = re.sub(r'        "Maximum altitude error".*?"Physical releases": deliv,', metric_block, data, flags=re.DOTALL)

with open("generate_report.py", "w") as f:
    f.write(data)
