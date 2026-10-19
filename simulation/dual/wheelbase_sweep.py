import math

wheelbases = [780, 750, 730, 720, 710, 700]
prop_dia = 457.2
safe_clearance = 15.0 # mm (minimum conservative)

print(f"{'Wheelbase':<10} | {'Spacing':<10} | {'Clearance':<10} | {'Footprint':<10} | {'Feasible'}")
print("-" * 65)

for d in wheelbases:
    s = d / math.sqrt(2)
    clearance = s - prop_dia
    footprint = s + prop_dia
    feasible = "YES" if clearance >= safe_clearance else "NO"
    
    print(f"{d:<10} | {s:<10.1f} | {clearance:<10.1f} | {footprint:<10.1f} | {feasible}")

