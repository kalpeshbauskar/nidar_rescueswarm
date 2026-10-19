#!/bin/bash
mkdir -p simulation/imported/humans/Standing_person/meshes
mkdir -p simulation/imported/humans/Walking_person/meshes
mkdir -p simulation/imported/humans/Casual_female/meshes

wget -q -O simulation/imported/humans/Standing_person/meshes/standing.dae "https://fuel.gazebosim.org/1.0/OpenRobotics/models/Standing%20person/1/files/meshes/standing.dae"
wget -q -O simulation/imported/humans/Walking_person/meshes/walking.dae "https://fuel.gazebosim.org/1.0/OpenRobotics/models/Walking%20person/1/files/meshes/walking.dae"
wget -q -O simulation/imported/humans/Casual_female/meshes/casual_female.dae "https://fuel.gazebosim.org/1.0/OpenRobotics/models/Casual%20female/1/files/meshes/casual_female.dae"
echo "Downloaded meshes."
