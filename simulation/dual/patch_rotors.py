import re
with open("build_world.py", "r") as f:
    data = f.read()

patch = """
    # Set exact 710mm wheelbase (0.251m in X/Y)
    for i_rotor in range(4):
        rl = m.find(f"link[@name='rotor_{i_rotor}']")
        if rl is not None:
            p = rl.find("pose")
            if p is not None:
                x = 0.251 if i_rotor in [0, 2] else -0.251
                y = 0.251 if i_rotor in [1, 2] else -0.251
                p.text = f"{x} {y} 0.06 0 0 0"
"""
# inject right before cleaning trailing whitespace
data = data.replace('raw_xml = E.tostring(w, encoding="unicode")', patch + '\nraw_xml = E.tostring(w, encoding="unicode")')

with open("build_world.py", "w") as f:
    f.write(data)
