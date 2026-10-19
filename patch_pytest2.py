import re

with open("tests/test_hardware_integration.py", "r") as f:
    data = f.read()

data = re.sub(
    r'def test_02_package_distribution.*?def test_03',
    '''def test_02_package_distribution(self):
        assert len(PAYLOAD_ALLOCATION) == 2
        assert PAYLOAD_ALLOCATION[0] == 5
        assert PAYLOAD_ALLOCATION[1] == 5
        assert sum(PAYLOAD_ALLOCATION) == TOTAL_PACKAGES
        assert TOTAL_PACKAGES == 10
        assert math.isclose(TOTAL_PAYLOAD_MASS_KG, 2.000, rel_tol=1e-5)

    def test_03''',
    data, flags=re.DOTALL
)

data = re.sub(
    r'def test_03_package_release_mass_reduction.*?def test_04',
    '''def test_03_package_release_mass_reduction(self):
        tracker = PayloadTracker(drone_id=0)
        assert tracker.packages_remaining == 5
        initial_auw = tracker.current_auw_kg

        for expected_remaining in [4, 3, 2, 1, 0]:
            prop_state = tracker.release_package(f"parcel_{5 - expected_remaining}")
            assert tracker.packages_remaining == expected_remaining
            expected_mass = tracker.dry_mass_kg + (expected_remaining * PACKAGE_MASS_KG)
            assert math.isclose(tracker.current_auw_kg, expected_mass, rel_tol=1e-4)
            assert tracker.current_auw_kg < initial_auw
            assert prop_state.tw_ratio >= MIN_TW_RATIO_REQUIRED

        with pytest.raises(RuntimeError):
            tracker.release_package("extra_package")

    def test_04''',
    data, flags=re.DOTALL
)

with open("tests/test_hardware_integration.py", "w") as f:
    f.write(data)
