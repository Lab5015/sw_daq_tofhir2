#!/usr/bin/sh
CONF=`cat /data1/cmsdaq/tofhir2/conf`
DATA_DIR=/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2b_jun22/config_${CONF}
mkdir -p ${DATA_DIR}

cp -r ../config_base/* ${DATA_DIR}/

#CONFIG_FILE=${DATA_DIR}/config_ith1_ith2_ithE.ini
CONFIG_FILE=${DATA_DIR}/config_ith1_ith2.ini


./acquire_threshold_calibration --config ${CONFIG_FILE} -o ${DATA_DIR}/disc_calibration 
./process_threshold_calibration --config ${CONFIG_FILE} -i  ${DATA_DIR}/disc_calibration -o ${DATA_DIR}/disc_calibration.tsv --root-file ${DATA_DIR}/disc_calibration.root

./make_simple_disc_settings_table --config ${CONFIG_FILE} --vth_t1 20 --vth_t2 20 --vth_e 15 -o ${DATA_DIR}/disc_settings.tsv

./acquire_tdc_calibration --config ${CONFIG_FILE} -o ${DATA_DIR}/tdc_calibration
./acquire_qdc_calibration --config ${CONFIG_FILE} -o ${DATA_DIR}/qdc_calibration

./process_tdc_calibration --config ${CONFIG_FILE} -i ${DATA_DIR}/tdc_calibration -o ${DATA_DIR}/tdc_calibration 
./process_qdc_calibration --config ${CONFIG_FILE} -i ${DATA_DIR}/qdc_calibration -o ${DATA_DIR}/qdc_calibration 

rm ../config
ln -s ${DATA_DIR} ../config

#source launch_aldoCalibs.sh
