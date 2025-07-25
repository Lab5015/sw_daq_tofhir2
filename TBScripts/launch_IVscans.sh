python acquire_sipm_IV_scan_K2000 --config ../config/config_ith1_ith2_ithE.ini --asic 0 --aldo A --ch 5 --bvMin 36 --bvMax 40  --nMeas 1 --verbose --fast
python acquire_sipm_IV_scan_K2000 --config ../config/config_ith1_ith2_ithE.ini --asic 0 --aldo B --ch 6 --bvMin 36 --bvMax 40  --nMeas 1 --verbose --fast
python acquire_sipm_IV_scan_K2000 --config ../config/config_ith1_ith2_ithE.ini --asic 2 --aldo A --ch 7 --bvMin 36 --bvMax 40  --nMeas 1 --verbose --fast
python acquire_sipm_IV_scan_K2000 --config ../config/config_ith1_ith2_ithE.ini --asic 2 --aldo B --ch 8 --bvMin 36 --bvMax 40  --nMeas 1 --verbose --fast

CONF=`cat /data1/cmsdaq/tofhir2/conf`
echo $CONF
python drawIVMerged.py --label $CONF
