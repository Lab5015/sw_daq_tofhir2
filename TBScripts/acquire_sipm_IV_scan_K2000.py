#!/usr/bin/env python

import sys
import os
sys.path.insert(1, os.path.join(sys.path[0], '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2b_jun22/build'))
from petsys import daqd, config
from copy import deepcopy
from time import sleep
import argparse
import ROOT
import math
from datetime import datetime
from ROOT import TFile
from collections import OrderedDict

sys.path.insert(1, os.path.join(sys.path[0], '/home/cmsdaq/DAQ/K2000'))
from K2000Wrapper import K2000



parser = argparse.ArgumentParser(description='Acquire SiPM IV scan')
parser.add_argument("--config", type=str, required=True, help="Configuration file")
parser.add_argument("--asic", type=int, required=True, help="ASIC ID")
parser.add_argument("--bvMin", type=str, dest="bvMin", required=True, help="starting bv")
parser.add_argument("--bvMax", type=str, dest="bvMax", required=True, help="ending bv")
parser.add_argument("--aldo", type=str, dest="aldo", required=True, help="which ALDO")
parser.add_argument("--ch", type=str, dest="ch", required=True, help="which channel of the keithley to measure")
parser.add_argument("--nMeas", type=str, dest="nMeas", required=False, help="number of measurements to average")
parser.add_argument("--label", type=str, dest="label", required=False, help="folder name")
parser.add_argument("--verbose", dest="verb", action="store_true", help="set to true to display output and plots, otherwise just save to root file")
parser.add_argument("--plot", dest="plot", action="store_true", help="set to true to display plots, otherwise just save to root file")
parser.add_argument("--calib", dest="calib", action="store_true", help="aldo calib")
parser.add_argument("--fast", dest="fast", action="store_true", help="perform fast IV scan") 
parser.add_argument("--dacStep", type=int, required=False, help="step in dac units", default=1)



#------------------------
# parsing input arguments
args = parser.parse_args()
verbose = False
if args.verb:
    verbose = True


#---------------------------------
# connect and configure multimeter
keithley = K2000('tcp://raspcmsroma01:8820')
print("logging SiPM current from Keithley channel number %d "%(int(args.ch)))
keithley.selectChannel(int(args.ch))


#--------------------
# read current config
f = open("/data1/cmsdaq/tofhir2/conf", "r")
conf = float(f.read())
f.close()


#-----------------------------
# load configuration from file
mask = config.LOAD_ALL
# if args.mode != "mixed":
#         mask ^= config.LOAD_QDCMODE_MAP
mask ^= config.LOAD_QDCMODE_MAP
systemConfig = config.ConfigFromFile(args.config, loadMask=mask)

daqd = daqd.Connection()
daqd.initializeSystem()
systemConfig.loadToHardware(daqd, bias_enable=config.APPLY_BIAS_OFF)

asicsConfig = daqd.getAsicsConfig()
activeAsics = daqd.getActiveAsics()

if len(activeAsics) == 0:
    print ("no active ASICs found. Exiting...")
    exit()
    
asicsConfig0 = deepcopy(asicsConfig)
cfg = deepcopy(asicsConfig0)

for portID, slaveID, chipID in activeAsics:
        if chipID%2 is not 0:
                continue
        if int(chipID) != args.asic:
            continue

        ac = cfg[(portID, slaveID, chipID)]
        gc = (cfg[(portID, slaveID, chipID)]).globalConfig
        gc.setValue("c_aldo_en", 0b00)
        daqd.setAsicsConfig(cfg)
        sleep(5.)
        stdout = keithley.getMeasure()
        sleep(2)
        
        print( "ALDO off   I: %f uA" % (abs(float(stdout.strip()))*1E06/10.))


#--------------
# define graphs
g_I = OrderedDict()
g_IV = ROOT.TGraph()
g_dlogIdV = ROOT.TGraph()


logfolder = '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2b_jun22/logs_%.2f/'%conf
if not os.path.exists(logfolder):
    os.mkdir(logfolder)
print logfolder


#--------------------------------
# print ALDO calibrations to file
if (args.calib):
    conf_folder = '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2b_jun22/config_%.2f/'%conf
    print conf_folder
    f_aldo = open('%s/aldo_scan_ASIC%d_ALDO%s'%(conf_folder,int(args.asic),args.aldo)+'.txt', "w")


#--------
# ov scan
for portID, slaveID, chipID in activeAsics:
        if chipID%2 is not 0:
                continue
        if int(chipID) != args.asic:
            continue
        
        print(portID,slaveID,chipID)
        
        ac = cfg[(portID, slaveID, chipID)]
        for dac in range(0,256,args.dacStep):
                if(not args.calib):
                    voltA, voltB = systemConfig.mapALDODACToVoltage((portID, slaveID, chipID),dac)
                    volt = 0.

                    if args.aldo is "A":
                        volt = float(voltA)                
                    if args.aldo is "B":
                        volt = float(voltB)
                    if volt < float(args.bvMin):
                        continue
                    if volt > float(args.bvMax):
                        break
                
                    g_I[volt] = ROOT.TGraph()
                
                gc = (cfg[(portID, slaveID, chipID)]).globalConfig
                if args.aldo is "A":
                    gc.setValue("c_aldo_en", 0b10)
                    gc.setValue("Valdo_A_DAC", dac)

                if args.aldo is "B":
                    gc.setValue("c_aldo_en", 0b01)
                    gc.setValue("Valdo_B_DAC", dac)

                daqd.setAsicsConfig(cfg)
                
                sleep(0.25)
                
                curr  = 0.
                vMeas = 0.
                nMeas = 1
                curr_list = []
                
                start_curr = 0.
                start_volt = 0.
                if (not args.fast):
                    stdout = keithley.getMeasure()
                    start_volt = abs(float(stdout.strip()))
                    start_curr = start_volt*1E06/10./1000. #to have it in mA
                    curr_list.append(start_curr)
                
                if args.nMeas:
                    nMeas = int(args.nMeas)
                if (not args.fast and not args.calib):
                    nMeas = 1 + int((start_curr/16.)*10)                    
                    print(start_curr,nMeas)
                
                it = 0
                for _ in range(nMeas):
                        sleep(0.25)
                        stdout = keithley.getMeasure()
                        this_volt = abs(float(stdout.strip()))
                        this_curr = this_volt*1E06/10.

                        if verbose:
                            if (not args.calib):
                                print ("dac: %3d   V_set: %6.3f V   V_meas: %f V -->  I: %f uA" % (int(dac),volt,this_volt,this_curr))
                            else:
                                print ("dac: %3d   V_meas: %f V" % (int(dac),this_volt))
                        if (not args.calib):
                            g_I[volt].SetPoint(g_I[volt].GetN(),g_I[volt].GetN(),this_curr)
                        else:
                            g_IV.SetPoint(g_IV.GetN(),g_IV.GetN(),this_volt)
                        
                        if it >= 0:
                                curr = curr + this_curr
                                vMeas = vMeas + this_volt
                        it += 1
                        # last5ave = 0
                        # print("nMeas = %f"%len(curr_list))
                        # if (len(curr_list)>7):
                        #     for i in range(5):
                        #         last5ave = last5ave + curr_list[len(curr_list)-i]
                        #         print("last5ave = %f, this_curr = %f"%(last5ave, this_curr))

                        #     if (this_curr>last5ave): 
                        #         break

                        # curr_list.append(this_curr)
                
                curr  = curr  / nMeas
                vMeas = vMeas / nMeas
                if (not args.calib):
                    g_IV.SetPoint(g_IV.GetN(),volt, curr)
                    print( "===> dac: %3d   V_set: %6.3f V_meas: %6.3f V -->  I: %f uA" % (int(dac),volt,vMeas,curr))
                else:
                    g_IV.SetPoint(g_IV.GetN(),int(dac), vMeas)
                    print( "%3d\t%f"%(int(dac),vMeas) )
                    f_aldo.write( "%3d\t%f\n"%(int(dac),vMeas) )


#-------------------------
# switch off bias voltages

for portID, slaveID, chipID in activeAsics:
        if chipID%2 is not 0:
                continue
        gc = (cfg[(portID, slaveID, chipID)]).globalConfig
        gc.setValue("c_aldo_en", 0b00)
daqd.setAsicsConfig(cfg)                                                                                                                                           


#---------
# plotting
for point in range(1,g_IV.GetN()):
    x1 = g_IV.GetPointX(point-1)
    x2 = g_IV.GetPointX(point)
    y1 = g_IV.GetPointY(point-1)
    y2 = g_IV.GetPointY(point)
    if x2 != x1:
        g_dlogIdV.SetPoint(g_dlogIdV.GetN(),0.5*(x1+x2),(math.log(y2)-math.log(y1))/(x2-x1))
    
if args.plot:
    c2 = ROOT.TCanvas("c2","c2",500,500)
    g_IV.SetTitle("I vs volt;volt [V]; I [#muA]")
    g_IV.Draw("APL")
    
    c3 = ROOT.TCanvas("c3","c3",500,500)
    g_dlogIdV.SetTitle("dlogIdV vs volt;volt [V]; #DeltalogI/#deltaV [#muA/V]")
    g_dlogIdV.Draw("APL")
    
    raw_input("ok?")

now = datetime.now()
this_time = now.strftime('%Y-%m-%d_%H:%M:%S')
if not args.label:
    args.label = '/'

if(not args.calib):
    logfile = '%s/logIV_ASIC%d_ALDO%s_ch%d_time_%s'%(logfolder,int(args.asic),args.aldo,int(args.ch),this_time)+'.root'
    print('saving data to: %s' % logfile)
    
    outFile = TFile(logfile,"RECREATE")
    outFile.cd()
    for volt in g_I.keys():
        g_I[volt].SetName('g_I_bv%.2f'%volt)
        g_I[volt].Write()
    g_IV.SetName("g_IV")
    g_IV.Write()
    g_dlogIdV.SetName("g_dlogIdV")
    g_dlogIdV.Write()
    outFile.Write()
    outFile.Close()
