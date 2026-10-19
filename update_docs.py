import re
import pathlib

DOCS = pathlib.Path("docs")

def patch_file(filename, replacements):
    path = DOCS / filename
    if not path.exists(): return
    content = path.read_text()
    for old, new in replacements:
        content = re.sub(old, new, content, flags=re.IGNORECASE)
    path.write_text(content)

# NIDAR_two_drone_final_validation_report.md
patch_file("NIDAR_two_drone_final_validation_report.md", [
    (r"45%|45\.0%", "80.2%"),
    (r"70\s*Wh", "70.4 Wh"),
    (r"5\.330", "5.280"),
    (r"6\.330", "6.280"),
    (r"12\.660", "12.560"),
    (r"780\s*mm", "710 mm"),
    (r"8\s*m/s", "10 m/s")
])
report = DOCS / "NIDAR_two_drone_final_validation_report.md"
if report.exists():
    with report.open("a") as f:
        f.write("\n## Rev-B Envelopes\n")
        f.write("- **700 x 700 x 420 mm** = non-propeller structural envelope\n")
        f.write("- **959 x 959 mm** = maximum rotating propeller-tip envelope\n")
        f.write("- **Final SOC** = 80.2%\n")
        f.write("- **Mission Energy** = 70.4 Wh / drone\n")

# two_drone_master_bom.md
patch_file("two_drone_master_bom.md", [
    (r"5\.330", "5.280"),
    (r"6\.330", "6.280"),
    (r"12\.660", "12.560"),
    (r"780", "710"),
    (r"Quadcopter Carbon Fiber Frame\s+\|\s+1\.300", "Rev-B Compact Quadcopter CF Frame (710mm) | 1.250")
])

# judge_demo_summary.md
patch_file("judge_demo_summary.md", [
    (r"5\.330", "5.280"),
    (r"6\.330", "6.280"),
    (r"780", "710"),
])

# judge_demo_checklist.md
patch_file("judge_demo_checklist.md", [
    (r"5\.330", "5.280"),
    (r"6\.330", "6.280"),
    (r"780", "710"),
])

