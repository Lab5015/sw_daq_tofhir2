#!/usr/bin/env python

import os
import argparse
import glob

parser = argparse.ArgumentParser(description='convert raw data')
parser.add_argument("--config", type=str, required=True, help="Configuration file")
parser.add_argument("-r", type=str, dest="run", required=True, help = "Run number")
parser.add_argument("--mode", type=str, required=True, choices=["r", "s", "c", "e"], help = "reconstruction mode (singles, coincicences or event)")
parser.add_argument("--refChannels", type=str, dest="refChannels", required=False, help = "reference channels")
parser.add_argument("--pedestals", dest="pedestals", action="store_true", help="Enable the acquisition of pedestals")

args = parser.parse_args()

if args.mode == 'r':
    command = "./convert_raw_to_raw --config "+args.config+" -i /data/tofhir2/h8/raw//run"+args.run+" -o /data/tofhir2/h8/reco//run"+args.run+"_r.root"
    os.system(command)

if args.mode == 's':
    mainCommand = "./convert_raw_to_singles --config "+args.config+" -i /data/tofhir2/h8/raw//run"+args.run+" --writeRoot"
    if args.pedestals:
        command = "./convert_raw_to_singles --config "+args.config+" -i /data/tofhir2/h8/raw//run"+args.run+"_ped1 -o /data/tofhir2/h8/reco//run"+args.run+"_ped1_s.root --writeRoot"
        os.system(command)
        command = "./convert_raw_to_singles --config "+args.config+" -i /data/tofhir2/h8/raw//run"+args.run+"_ped2 -o /data/tofhir2/h8/reco//run"+args.run+"_ped2_s.root --writeRoot"
        os.system(command)
        command = "./analyze_pedestals.exe /data/tofhir2/h8/reco//run"+args.run+"_ped1_s.root /data/tofhir2/h8/reco//run"+args.run+"_ped2_s.root /data/tofhir2/h8/reco//run"+args.run+"_pedestals.root"
        os.system(command)
        mainCommand += " --pedestals -o /data/tofhir2/h8/reco//run"+args.run+"_ped_s.root"
    else:
        mainCommand += " -o /data/tofhir2/h8/reco//run"+args.run+"_s.root"
    os.system(mainCommand)

if args.mode == 'c':
    command = "./convert_raw_to_coincidence --config "+args.config+" -i /data/tofhir2/h8/raw//run"+args.run+" -o /data/tofhir2/h8/reco//run"+args.run+"_c.root --writeRoot"
    os.system(command)

if args.mode == 'e':
    folder = '/data/tofhir2/raw/'
    infile = '%s/run%s.rawf'%(folder,args.run)
    basename = infile.replace('.rawf','')
    
    command = "mkdir /data/tofhir2/reco/"+args.run+"/"
    os.system(command)
    mainCommand = "./convert_raw_to_event --config "+args.config+" -i "+basename+" --writeRoot"
    print mainCommand
    if args.pedestals:
        #command = "./convert_raw_to_singles --config "+args.config+" -i /data/tofhir2/h8/raw//run"+args.run+"_ped1 -o /data/tofhir2/h8/reco//run"+args.run+"_ped1_s.root --writeRoot"
        #os.system(command)
        #command = "./convert_raw_to_singles --config "+args.config+" -i /data/tofhir2/h8/raw//run"+args.run+"_ped2 -o /data/tofhir2/h8/reco//run"+args.run+"_ped2_s.root --writeRoot"
        #os.system(command)
        #command = "./analyze_pedestals.exe /data/tofhir2/h8/reco//run"+args.run+"_ped1_s.root /data/tofhir2/h8/reco//run"+args.run+"_ped2_s.root /data/tofhir2/h8/reco//run"+args.run+"_pedestals.root"
        #os.system(command)
        command = "ln -sf "+pedestal_file+" "+basename+"_pedestals.root"
        command = command.replace('/raw/','/reco/')
        os.system(command)
        mainCommand += " --pedestals -o /data/tofhir2/reco/"+args.run+"/1_ped_e.root"
        print mainCommand
    else:
        mainCommand += " -o /data/tofhir2/reco/"+args.run+"/1_e.root"
        print mainCommand
        if args.refChannels :
            mainCommand += " --coincidence --refChannels "+args.refChannels
    os.system(mainCommand)
            
