#!/usr/bin/env python
from __future__ import print_function
import os
import argparse

parser = argparse.ArgumentParser(description='convert raw data')
parser.add_argument("--config", type=str, required=True, help="Configuration file")
parser.add_argument("-r", "--run", type=str, required=True, help="Run number")
parser.add_argument("--mode", type=str, required=True, choices=["r", "s", "c", "e"], help = "reconstruction mode (singles, coincicences or event)")
parser.add_argument("--refChannel", type=str, required=False, help = "reference channel")
parser.add_argument("--pedestals", dest="pedestals", action="store_true", help="Enable the acquisition of pedestals")
parser.add_argument("--data-dir", default="/storage/TOFHIR2", help="Directory to store raw and reco data")
args = parser.parse_args()

if not os.path.exists(args.data_dir):
    print("Error: data directory '%s' does not exist!" % args.data_dir)
    print("Please rerun with --data-dir specifying where output data is")

raw_prefix = os.path.join(args.data_dir,"raw",args.run)
reco_prefix = os.path.join(args.data_dir,"reco","%s" % args.run)

if args.mode == 'r':
    command = "./convert_raw_to_raw --config %s -i %s -o %s_r.root" % (args.config, raw_prefix, reco_prefix)
    os.system(command)

if args.mode == 's':
    mainCommand = "./convert_raw_to_singles --config %s -i %s --writeRoot" % (args.config, raw_prefix)
    if args.pedestals:
        command = "./convert_raw_to_singles --config %s -i %s_ped1 -o %s_ped1_s.root --writeRoot" % (args.config, raw_prefix, reco_prefix)
        os.system(command)
        command = "./convert_raw_to_singles --config %s -i %s_ped2 -o %s_ped2_s.root --writeRoot" % (args.config, raw_prefix, reco_prefix)
        os.system(command)
        command = "./analyze_pedestals.exe %s_ped1_s.root %s_ped2_s.root %s_pedestals.root" % (raw_prefix, raw_prefix, reco_prefix)
        os.system(command)
        mainCommand += " --pedestals -o %s_ped_s.root" % reco_prefix
    else:
        mainCommand += " -o %s_s.root" % reco_prefix
    os.system(mainCommand)

if args.mode == 'c':
    command = "./convert_raw_to_coincidence --config %s -i %s -o %s_c.root --writeRoot" % (args.config, raw_prefix, reco_prefix)
    os.system(command)

if args.mode == 'e':
    mainCommand = "./convert_raw_to_event --config %s -i %s --writeRoot" % (args.config, raw_prefix)
    if args.pedestals:
        command = "./convert_raw_to_singles --config %s -i %s_ped1 -o %s_ped1_s.root --writeRoot" % (args.config, raw_prefix, reco_prefix)
        os.system(command)
        command = "./convert_raw_to_singles --config %s -i %s_ped2 -o %s_ped2_s.root --writeRoot" % (args.config, raw_prefix, reco_prefix)
        os.system(command)
        command = "./analyze_pedestals.exe %s_ped1_s.root %s_ped2_s.root %s_pedestals.root" % (raw_prefix, raw_prefix, reco_prefix)
        os.system(command)
        mainCommand += " --pedestals -o %s_ped_e.root" % reco_prefix
    else:
        mainCommand += " -o %s_e.root" % reco_prefix
    if args.refChannel :
        mainCommand += " --refChannel %s" % args.refChannel
    os.system(mainCommand)
