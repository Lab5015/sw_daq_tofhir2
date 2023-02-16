#! /usr/bin/python

import os
import sys
import ROOT
import time
from ROOT import *
from optparse import OptionParser
from datetime import datetime


parser = OptionParser()
parser.add_option("--folder")
parser.add_option("--run")
(options,args)=parser.parse_args()

timestamp_first = 0
timestamp_last = 0

graphs = {}

for it in range(0, 2, 1):
    graphs[it] = ROOT.TGraph()

logfile = '%s/logTECs_%03d'%(options.folder,int(options.run))+'.txt' 
#logfile = 'temp.log' 
   
with open(logfile, 'r') as fin:
    for line in fin.readlines():
        readings = line.strip().split()
        
        if 'Fault' in readings:
            continue
        
        date = datetime.strptime(readings[0]+" "+readings[1], '%Y-%m-%d %H:%M:%S')
        timestamp = time.mktime(date.timetuple())
        if timestamp_first == 0:
            timestamp_first = timestamp
        if timestamp > timestamp_last:
            timestamp_last = timestamp
        
        for it in range(0, 2, 1):
            graph = graphs[it]
            temp = float((readings[3+it]))
            graph.SetPoint(graph.GetN(),(timestamp-timestamp_first)/60.,temp)

c1 = ROOT.TCanvas('','',1300,600)
c1.SetGridx()
c1.SetGridy()
hPad1 = ROOT.gPad.DrawFrame(0.-0.05*(timestamp_last-timestamp_first)/60.,-50.,1.05*(timestamp_last-timestamp_first)/60.,30.)
hPad1.SetTitle(";time elapsed [min];T [#circ C]")
hPad1.Draw()

for it in range(0, 2, 1):
    graph = graphs[it]
    graph.SetLineStyle(1+it/2)
    graph.SetLineColor(1+it%2)
    graph.SetMarkerColor(1+it%2)
    graph.Draw("PL,same")

raw_input('ok?')
