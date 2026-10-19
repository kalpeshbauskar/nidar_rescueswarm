import json, subprocess, xml.etree.ElementTree as E

for count in range(6, 11):
    cfg = json.loads(open('simulation/dual/config.json').read())
    cfg['active_profile'] = 'dual_drone_legacy'
    cfg['profiles']['dual_drone_legacy']['drones'][0]['packages'] = count
    cfg['profiles']['dual_drone_legacy']['drones'][1]['packages'] = count
    with open('simulation/dual/config.json', 'w') as f:
        json.dump(cfg, f, indent=2)
    
    subprocess.run(['python3', 'simulation/dual/build_world.py'], capture_output=True)
    
    sdf = E.parse('simulation/dual/dual_rescue.sdf').getroot()
    world = sdf.find('world')
    
    # Check parcel count
    parcels_0 = len([m for m in world.findall('model') if m.get('name', '').startswith('parcel_0_')])
    parcels_1 = len([m for m in world.findall('model') if m.get('name', '').startswith('parcel_1_')])
    
    # Check detachable joints in rescue_0
    rescue_0 = [m for m in world.findall('model') if m.get('name') == 'rescue_0'][0]
    joints_0 = len([p for p in rescue_0.findall('plugin') if p.get('filename') == 'gz-sim-detachable-joint-system'])
    
    # Check mass of parcel_0_0
    parcel_0_0 = [m for m in world.findall('model') if m.get('name') == 'parcel_0_0'][0]
    mass = float(parcel_0_0.find('.//mass').text)
    
    print(f"Count {count}: D0_Parcels={parcels_0}, D1_Parcels={parcels_1}, Joints_0={joints_0}, Mass={mass}, Total Payload={count*mass:.1f}kg")

# Restore competition_3drone
cfg = json.loads(open('simulation/dual/config.json').read())
cfg['active_profile'] = 'competition_3drone'
with open('simulation/dual/config.json', 'w') as f:
    json.dump(cfg, f, indent=2)
subprocess.run(['python3', 'simulation/dual/build_world.py'], capture_output=True)
