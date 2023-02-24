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


# ML_Models/transfuser-2022/team_code_transfuser
echo "3.Downloading the transfuser model weights"
wget https://s3.eu-central-1.amazonaws.com/avg-projects/transfuser/models_2022.zip -P .
unzip models_2022.zip -d .
mv models_2022/ model_ckpt/
rm models_2022.zip
mv model_ckpt/ MLMAS_Project/ML_Models/transfuser-2022/




echo "4.Downloading CARLA 0.9.10.1 with the required AdditionalMaps"
mkdir CARLA_0.9.10.1
cd CARLA_0.9.10.1
wget https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/CARLA_0.9.10.1.tar.gz
wget https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/AdditionalMaps_0.9.10.1.tar.gz

echo "5.Extracting CARLA and MAP folders"
tar -xf CARLA_0.9.10.1.tar.gz
tar -xf AdditionalMaps_0.9.10.1.tar.gz

rm CARLA_0.9.10.1.tar.gz
rm AdditionalMaps_0.9.10.1.tar.gz

cd ..
mv CARLA_0.9.10.1/ MLMAS_Project/

echo "Finish: The project folder is ready"
