import re

with open("tests/test_hardware_integration.py", "r") as f:
    data = f.read()

# Test 2: Package distribution
data = data.replace(
    'assert len(PAYLOAD_ALLOCATION) == 3\n        assert sum(PAYLOAD_ALLOCATION) == 10\n        assert PAYLOAD_ALLOCATION == (4, 4, 2)',
    'assert len(PAYLOAD_ALLOCATION) == 2\n        assert sum(PAYLOAD_ALLOCATION) == 10\n        assert PAYLOAD_ALLOCATION == (5, 5)'
)

# Test 3: Mass reduction
data = data.replace(
    'assert tracker.packages_remaining == 4',
    'assert tracker.packages_remaining == 5'
)
data = data.replace(
    'assert math.isclose(tracker.current_package_mass_kg, 0.8, rel_tol=1e-4)',
    'assert math.isclose(tracker.current_package_mass_kg, 1.0, rel_tol=1e-4)'
)
data = data.replace(
    'tracker.drop_package()  # 4->3\n        assert tracker.packages_remaining == 3\n        assert math.isclose(tracker.current_package_mass_kg, 0.6, rel_tol=1e-4)',
    'tracker.drop_package()  # 5->4\n        assert tracker.packages_remaining == 4\n        assert math.isclose(tracker.current_package_mass_kg, 0.8, rel_tol=1e-4)'
)

# Test 5: Fleet combined AUW
data = data.replace(
    'assert 17.0 <= fleet_auw <= 21.0',
    'assert 12.0 <= fleet_auw <= 13.0'
)

# Test 8: Battery energy
data = data.replace(
    'assert math.isclose(BATTERY_SPECS.nominal_energy_wh, 266.4, rel_tol=1e-4)',
    'assert math.isclose(BATTERY_SPECS.nominal_energy_wh, 355.2, rel_tol=1e-4)'
)
data = data.replace(
    'assert math.isclose(BATTERY_SPECS.usable_energy_wh, 213.12, rel_tol=1e-4)',
    'assert math.isclose(BATTERY_SPECS.usable_energy_wh, 284.16, rel_tol=1e-4)'
)
data = data.replace(
    'assert math.isclose(BATTERY_SPECS.reserve_energy_wh, 53.28, rel_tol=1e-4)',
    'assert math.isclose(BATTERY_SPECS.reserve_energy_wh, 71.04, rel_tol=1e-4)'
)

# Test 10: 30 minute maximum rule logic
data = data.replace(
    'integrator.energy_consumed_wh = 230.0',
    'integrator.energy_consumed_wh = 300.0'
)

with open("tests/test_hardware_integration.py", "w") as f:
    f.write(data)
