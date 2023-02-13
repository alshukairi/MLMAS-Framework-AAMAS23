#!/bin/bash
# (C) University of Aberdeen
# Hilal Al Shukairi
echo "1.Downloading the LAV model weights"
mkdir tmp
cd tmp
wget https://github.com/alshukairi/public/raw/main/LAV_Weight/LAV_weights.zip.000
wget https://github.com/alshukairi/public/raw/main/LAV_Weight/LAV_weights.zip.001
wget https://github.com/alshukairi/public/raw/main/LAV_Weight/LAV_weights.zip.002
cat LAV_weights.zip.* > ../LAV_weights.zip

echo "2.Extract the LAV weights folder"
cd ..
unzip LAV_weights.zip
mv weights/ MLMAS_Project/ML_Models/LAV/
rm -R tmp
rm LAV_weights.zip

echo "3.Downloading CARLA 0.9.10.1 with the required AdditionalMaps"
mkdir CARLA_0.9.10.1
cd CARLA_0.9.10.1
wget https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/CARLA_0.9.10.1.tar.gz
wget https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/AdditionalMaps_0.9.10.1.tar.gz

echo "4.Extracting CARLA and MAP folders"
tar -xf CARLA_0.9.10.1.tar.gz
tar -xf AdditionalMaps_0.9.10.1.tar.gz

rm CARLA_0.9.10.1.tar.gz
rm AdditionalMaps_0.9.10.1.tar.gz

cd ..
mv CARLA_0.9.10.1/ MLMAS_Project/

echo "Finish: The project folder is ready"
