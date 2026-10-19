def estimate_power(mass, speed, frontal_area_factor):
    # SIMULATION / ENGINEERING ESTIMATE
    # Hover power ~ mass * 45 W/kg
    hover_p = mass * 45.0
    # Drag power ~ v^3 * area_factor
    drag_p = (speed ** 3) * 0.25 * frontal_area_factor
    return hover_p + drag_p

print("REV-A Power:")
print(f"5 m/s: {estimate_power(6.330, 5, 1.0):.0f} W")
print(f"7 m/s: {estimate_power(6.330, 7, 1.0):.0f} W")
print(f"8 m/s: {estimate_power(6.330, 8, 1.0):.0f} W")
print(f"10 m/s: {estimate_power(6.330, 10, 1.0):.0f} W")

print("\nREV-B Power:")
print(f"5 m/s: {estimate_power(6.280, 5, 0.95):.0f} W")
print(f"7 m/s: {estimate_power(6.280, 7, 0.95):.0f} W")
print(f"8 m/s: {estimate_power(6.280, 8, 0.95):.0f} W")
print(f"10 m/s: {estimate_power(6.280, 10, 0.95):.0f} W")
