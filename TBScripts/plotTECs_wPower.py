#! /usr/bin/python

import sys
import ROOT
from ROOT import *
import time
from datetime import datetime

timestamp_first = 0
timestamp_last = 0

graphs = {}
graphsV = {}
graphsI = {}
graphsW = {}
graphsR = {}

for it in range(0, 4, 1):
    graphs[it]  = ROOT.TGraph()
    graphs[it].SetTitle(Form("T: ASIC %d, side %d"%(it%2*2,it/2) ) )
    graphsV[it] = ROOT.TGraph()
    graphsV[it].SetTitle(Form("V: ASIC %d, side %d"%(it%2*2,it/2) ) )
    graphsI[it] = ROOT.TGraph()
    graphsI[it].SetTitle(Form("I: ASIC %d, side %d"%(it%2*2,it/2) ) )
    graphsW[it] = ROOT.TGraph()
    graphsW[it].SetTitle(Form("W: ASIC %d, side %d"%(it%2*2,it/2) ) )
    graphsR[it] = ROOT.TGraph()
    graphsR[it].SetTitle(Form("R: ASIC %d, side %d"%(it%2*2,it/2) ) )
    
f = open("/data/tofhir2/conf", "r")
conf = float(f.read())
conf = 26
f.close()
timerange=10

with open('/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2x/logs_%.2f/logTECs_001.txt'%conf, 'r') as fin:
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
            graphV = graphsV[it+add]
            graphI = graphsI[it+add]
            graphW = graphsW[it+add]
            graphR = graphsR[it+add]

            graph.SetPoint(graph.GetN(),(timestamp-timestamp_first)/60.,float(readings[it+3]))
            volt = float(readings[it*4+5])
#            print ("volt = ", volt)
            graphV.SetPoint(graphV.GetN(),(timestamp-timestamp_first)/60.,volt)
            current = float(readings[it*4+7])
#            print ("current = ", current)
            graphI.SetPoint(graphI.GetN(),(timestamp-timestamp_first)/60.,current)

            graphW.SetPoint(graphW.GetN(),(timestamp-timestamp_first)/60.,volt*current)
            if (current!=0): graphR.SetPoint(graphR.GetN(),(timestamp-timestamp_first)/60.,volt/current)

c1 = ROOT.TCanvas('cTemp','cTemp',1300,600)
#c1.Divide(1,5)
#c1.cd(1)
c1.SetGridx()
c1.SetGridy()
hPad1 = ROOT.gPad.DrawFrame(0.-0.05*(timestamp_last-timestamp_first)/60.,-50.,1.05*(timestamp_last-timestamp_first)/60.,30.)
hPad1.SetTitle(";time elapsed [min];T [#circ C]")
hPad1.Draw()

for it in range(0, 4, 1):
    graph = graphs[it]
    graph.SetLineStyle(1+it/2)
    graph.SetLineColor(1+it)
    graph.SetMarkerColor(1+it)
    graph.Draw("PL,same")
gPad.BuildLegend()

c2 = ROOT.TCanvas('cVoltage','cVoltage',1300,600)
c2.SetGridx()
c2.SetGridy()
c1.cd(2)
hPad1 = ROOT.gPad.DrawFrame(0.-0.05*(timestamp_last-timestamp_first)/60.,0.,1.05*(timestamp_last-timestamp_first)/60.,10.)
hPad1.SetTitle(";time elapsed [min];V [V]")
hPad1.Draw()

for it in range(0, 4, 1):
    graphV = graphsV[it]
    graphV.SetLineStyle(1+it/2)
    graphV.SetLineColor(1+it)
    graphV.SetMarkerColor(1+it)
    graphV.Draw("PL,same")
gPad.BuildLegend()


c3 = ROOT.TCanvas('cCurrent','cCurrent',1300,600)
c3.SetGridx()
c3.SetGridy()
#c1.cd(3)
hPad1 = ROOT.gPad.DrawFrame(0.-0.05*(timestamp_last-timestamp_first)/60.,0.,1.05*(timestamp_last-timestamp_first)/60.,1.)
hPad1.SetTitle(";time elapsed [min];I [A]")
hPad1.Draw()

for it in range(0, 4, 1):
    graphI = graphsI[it]
    graphI.SetLineStyle(1+it/2)
    graphI.SetLineColor(1+it)
    graphI.SetMarkerColor(1+it)
    graphI.Draw("PL,same")
gPad.BuildLegend()

c4 = ROOT.TCanvas('cPower','cPower',1300,600)
c4.SetGridx()
c4.SetGridy()
#c1.cd(4)
hPad1 = ROOT.gPad.DrawFrame(0.-0.05*(timestamp_last-timestamp_first)/60.,0.,1.05*(timestamp_last-timestamp_first)/60.,10.)
#hPad1 = ROOT.gPad.DrawFrame(0.timestamp_last/60.-timerange,0.,1.05*(timestamp_last-timestamp_first)/60.,5000.)
hPad1.SetTitle(";time elapsed [min];Power [W]")
hPad1.Draw()

for it in range(0, 4, 1):
    graphW = graphsW[it]
    graphW.SetLineStyle(1+it/2)
    graphW.SetLineColor(1+it)
    graphW.SetMarkerColor(1+it)
    graphW.Draw("PL,same")
gPad.BuildLegend()

c5 = ROOT.TCanvas('cResistance','cResistance',1300,600)
c5.SetGridx()
c5.SetGridy()
#c1.cd(5)
hPad1 = ROOT.gPad.DrawFrame(0.-0.05*(timestamp_last-timestamp_first)/60.,0.,1.05*(timestamp_last-timestamp_first)/60.,100.)
#print("timelast = ", timestamp_last/60.)
#hPad1 = ROOT.gPad.DrawFrame(timestamp_last/60.-timerange,0.,1.05*(timestamp_last-timestamp_first)/60.,200.)
hPad1.SetTitle(";time elapsed [min];Resistance [#Omega]")
hPad1.Draw()

for it in range(0, 4, 1):
    graphR = graphsR[it]
    graphR.SetLineStyle(1+it/2)
    graphR.SetLineColor(1+it)
    graphR.SetMarkerColor(1+it)
    graphR.Draw("PL,same")
#    gPad.SetLogy()

gPad.BuildLegend()

raw_input('ok?')
