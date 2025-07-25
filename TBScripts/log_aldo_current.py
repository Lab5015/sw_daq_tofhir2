#!/usr/bin/env python
import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '../build_new/'))
from petsys import daqd, config
from time import sleep
import argparse
from datetime import datetime
from ROOT import TFile
import logging

sys.path.insert(1, os.path.join(sys.path[0], '/home/cmsdaq/DAQ/K2000'))
from K2000Wrapper import K2000

parser = argparse.ArgumentParser(description='log ALDO CURRENTS')
parser.add_argument("--ch", type=str, dest="ch", required=True, help="which channel of the keithley to measure")
parser.add_argument("--filename", type=str, dest="filename", required=True, help="log file")

# parsing input arguments
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', filename=args.filename, encoding='utf-8', level=logging.INFO)
# connect and configure multimeter
keithley = K2000('tcp://raspcmsroma01:8820')
print("logging SiPM current from Keithley channel number %d "%(int(args.ch)))
keithley.selectChannel(int(args.ch))

while(True):
    stdout = keithley.getMeasure()
    logging.info("ch%d   I: %f uA" % (int(args.ch),abs(float(stdout.strip()))*1E06/10.))
