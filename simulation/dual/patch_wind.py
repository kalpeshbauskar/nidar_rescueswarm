import sys, re

def add_wind(sdf_path, speed_mps, direction_x=0.0):
    if speed_mps <= 0.001:
        print(f"[WIND] Zero wind requested ({speed_mps:.1f} m/s). Keeping environment calm and level.")
        return

    with open(sdf_path, 'r') as f:
        sdf = f.read()
        
    wind_plugin = f"""
    <plugin filename="gz-sim-wind-effects-system" name="gz::sim::systems::WindEffects">
      <force_approximation_scaling_factor>1</force_approximation_scaling_factor>
      <horizontal>
        <magnitude>
          <time_for_rise>1</time_for_rise>
          <sin>
            <amplitude_percent>0</amplitude_percent>
            <period>60</period>
          </sin>
          <noise type="none"></noise>
        </magnitude>
        <direction>
          <time_for_rise>1</time_for_rise>
          <sin>
            <amplitude>0</amplitude>
            <period>20</period>
          </sin>
          <noise type="none"></noise>
        </direction>
      </horizontal>
      <vertical>
        <noise type="none"></noise>
      </vertical>
    </plugin>
"""
    # Use constant wind direction (X or Y), speed = speed_mps
    wind_tag = f"""
    <wind>
      <linear_velocity>0 {speed_mps} 0</linear_velocity>
    </wind>
"""
    # Add wind plugin and wind velocity
    sdf = sdf.replace("</world>", wind_plugin + wind_tag + "\n</world>")
    
    # Add <enable_wind>true</enable_wind> ONLY to dynamic models (rescue drones, rotors, and parcels)
    # Exclude static scenery (water, debris, survivors) and sensitive sensor links (camera_link)
    dynamic_links = {"base_link", "rotor_0", "rotor_1", "rotor_2", "rotor_3", "body", "rack_link"}
    def _add_wind_to_link(match):
        tag = match.group(0)
        link_name = match.group(1)
        if link_name in dynamic_links:
            return f'{tag}\n        <enable_wind>true</enable_wind>'
        return tag

    sdf = re.sub(r'<link\s+name="([^"]+)">', _add_wind_to_link, sdf)
    
    with open(sdf_path, 'w') as f:
        f.write(sdf)

if __name__ == '__main__':
    speed = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    target_sdf = sys.argv[2] if len(sys.argv) > 2 else 'dual_rescue.sdf'
    add_wind(target_sdf, speed)

