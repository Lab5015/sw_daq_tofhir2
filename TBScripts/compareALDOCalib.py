#! /usr/bin/python

import sys
import ROOT
from ROOT import *
import time
from collections import OrderedDict
from datetime import datetime

infiles = OrderedDict()
#infiles['18C'] = '../config/ALDO_T2TB_C07_2022_03_07_18C_Tahereh/A0_ALDO_A_high.tsv'
#infiles['0C'] = '../config/ALDO_T2TB_C07_2022_03_15_0C_noModule/A0_ALDO_A_high.tsv'
#infiles['-10C'] = '../config/ALDO_T2TB_C07_2022_03_15_-10C_noModule/A0_ALDO_A_high.tsv'
#infiles['-20C'] = '../config/ALDO_T2TB_C07_2022_03_15_-20C_noModule/A0_ALDO_A_high.tsv'
#infiles['-30C'] = '../config/ALDO_T2TB_C07_2022_03_15_-30C_noModule/A0_ALDO_A_high.tsv'
#infiles['-40C'] = '../config/ALDO_T2TB_C07_2022_03_15_-36C_noModule/A0_ALDO_A_high.tsv'
#ref = '18C'

#infiles['15C'] = '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2_pedSubtraction_tb/config/ALDO_T2TB03_TofHIR2A_2022_03_24_15C/aldo_calibration_A_high.tsv'
#infiles['0C'] = '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2_pedSubtraction_tb/config/ALDO_T2TB03_TofHIR2A_2022_03_17_0C/A0_ALDO_A_high.tsv'
#infiles['-35C'] = '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2_pedSubtraction_tb/config/ALDO_T2TB03_TofHIR2A_2022_03_18_-35C/aldo_calibration_A_high.tsv'
#ref = '0C'

infiles['0C'] = '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2_pedSubtraction_tb/config/ALDO_T2TB03_TofHIR2A_2022_03_31_0C/aldo_calibration_A_high.tsv'
infiles['-35C'] = '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2_pedSubtraction_tb/config/ALDO_T2TB03_TofHIR2A_2022_03_31_-35C/aldo_calibration_A_high.tsv'
ref = '0C'

#infiles['20C'] = '../config/ALDO_T2TB_C08_2022_03_30_20C/aldo_calibration_A_high.tsv'
#infiles['0C'] = '../config/ALDO_T2TB_C08_2022_03_30_0C/aldo_calibration_A_high.tsv'
#infiles['-35C'] = '../config/ALDO_T2TB_C08_2022_03_30_-35C/aldo_calibration_A_high.tsv'
#ref = '20C'

graphs = {}
graphs_diff = {}
graphs_deltaV = {}

for key in infiles.keys():
    infile = infiles[key]
    
    graphs[key] = ROOT.TGraph()
    graphs_diff[key] = ROOT.TGraph()
    graphs_deltaV[key] = ROOT.TGraph()

    it = 0
    with open(infile) as f:
        for line in f:
            vals = line.split()
            graphs[key].SetPoint(int(vals[0]),float(vals[0]),float(vals[1]))
            
            if it > 0:
                graphs_deltaV[key].SetPoint(int(vals[0]),float(vals[0]),graphs[key].GetPointY(it)-graphs[key].GetPointY(it-1))
            
            it += 1

for key in infiles.keys():
    if key == ref:
        continue
    for point in range(0,graphs[key].GetN()):
        graphs_diff[key].SetPoint(point,graphs[key].GetPointX(point),graphs[key].GetPointY(point)-graphs[ref].GetPointY(point))

c1 = ROOT.TCanvas('','',1800,600)
c1.Divide(3,1)
c1.cd(1)
ROOT.gPad.SetGridx()
ROOT.gPad.SetGridy()
hPad1 = ROOT.gPad.DrawFrame(-1.,30.,256.,47.)
#hPad1 = ROOT.gPad.DrawFrame(-1.,24.,256.,36.)
hPad1.SetTitle(";DAC;V_{out} [V]")
hPad1.Draw()

it = 0
for key in infiles.keys():
    it += 1
    graph = graphs[key]
    graph.SetLineColor(it)
    graph.Draw("L,same")

c1.cd(2)
ROOT.gPad.SetGridx()
ROOT.gPad.SetGridy()
hPad2 = ROOT.gPad.DrawFrame(-1.,-0.75,256.,0.25)
hPad2.SetTitle(";DAC;diff. V_{out} [V]")
hPad2.Draw()

it = 0
for key in infiles.keys():
    it += 1
    if key == ref:
        continue
    graph = graphs_diff[key]
    graph.SetLineColor(it)
    graph.Draw("L,same")

c1.cd(3)
ROOT.gPad.SetGridx()
ROOT.gPad.SetGridy()
hPad3 = ROOT.gPad.DrawFrame(-1.,0.,256.,0.1)
hPad3.SetTitle(";DAC; #DeltaV_{out}/DAC [V]")
hPad3.Draw()

it = 0
for key in infiles.keys():
    it += 1
    graph = graphs_deltaV[key]
    graph.SetLineColor(it)
    graph.Draw("L,same")

raw_input('ok?')
