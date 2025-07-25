#! /usr/bin/python

import sys
import ROOT
from ROOT import *
import time
from datetime import datetime

timestamp_first = 0
timestamp_last = 0

graphs = {}

for it in range(0, 4, 1):
    graphs[it] = ROOT.TGraph()
    
f = open("/data1/cmsdaq/tofhir2/conf", "r")
conf = float(f.read())
f.close()

with open('/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2b_jun22/logs_14.03/logTECs_001.txt', 'r') as fin:
    for line in fin.readlines():
        
        readings = line.strip().split()

        date = datetime.strptime(readings[0]+" "+readings[1], '%Y-%m-%d %H:%M:%S')
        timestamp = time.mktime(date.timetuple())
        if timestamp_first == 0:
            timestamp_first = timestamp
        if timestamp > timestamp_last:
            timestamp_last = timestamp
        
        add = 0
        if readings[2] == 'ASIC2':
            add = 2
        
        for it in range(0, 2, 1):
            graph = graphs[it+add]
            graph.SetPoint(graph.GetN(),(timestamp-timestamp_first)/60.,float(readings[it+3]))

c1 = ROOT.TCanvas('','',1300,600)
c1.SetGridx()
c1.SetGridy()
hPad1 = ROOT.gPad.DrawFrame(0.-0.05*(timestamp_last-timestamp_first)/60.,-50.,1.05*(timestamp_last-timestamp_first)/60.,30.)
hPad1.SetTitle(";time elapsed [min];T [#circ C]")
hPad1.Draw()

for it in range(0, 4, 1):
#for it in range(2, 4, 1):
    graph = graphs[it]
    graph.SetLineStyle(1+it/2)
    graph.SetLineColor(1+it%2)
    graph.SetMarkerColor(1+it%2)
    graph.Draw("PL,same")

raw_input('ok?')
