python setALDOBias.py --power 1

echo "doing asic 0 aldo A"
python acquire_sipm_IV_scan_K2000 --config ../config/config_ith1_ith2_ithE.ini --asic 0 --aldo A --ch 3 --bvMin 0 --bvMax 100  --nMeas 1 --verbose --calib 
echo "doing asic 0 aldo B"
python acquire_sipm_IV_scan_K2000 --config ../config/config_ith1_ith2_ithE.ini --asic 0 --aldo B --ch 4 --bvMin 0 --bvMax 100  --nMeas 1 --verbose --calib
echo "doing asic 2 aldo A"
python acquire_sipm_IV_scan_K2000 --config ../config/config_ith1_ith2_ithE.ini --asic 2 --aldo A --ch 1 --bvMin 0 --bvMax 100  --nMeas 1 --verbose --calib
echo "doing asic 2 aldo B"
python acquire_sipm_IV_scan_K2000 --config ../config/config_ith1_ith2_ithE.ini --asic 2 --aldo B --ch 2 --bvMin 0 --bvMax 100  --nMeas 1 --verbose --calib

echo "merging ALDO calibs..."
python create_ALDO_calibration_combined.py

CONF=`cat /data1/cmsdaq/tofhir2/conf`
echo $CONF
python plot_ALDO_calibration_combined.py --label $CONF
