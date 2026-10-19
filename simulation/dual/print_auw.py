import sys
sys.path.append('..')
from hardware.config import get_drone_initial_auw_kg
print("New Loaded AUW:", get_drone_initial_auw_kg(0))
