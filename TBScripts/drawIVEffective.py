#! /usr/bin/python

import os
import sys
import ROOT
import time
from ROOT import *
from optparse import OptionParser
from datetime import datetime


parser = OptionParser()
parser.add_option("--infilename")
parser.add_option("--Vbr")
(options,args)=parser.parse_args()


infile_IV_TB = ROOT.TFile(options.infilename)
g_IV = infile_IV_TB.Get('g_IV')

graph_IVeff_TB = ROOT.TGraph()
graph_DCR_TB = ROOT.TGraph()

for point in range(g_IV.GetN()):
    x = g_IV.GetPointX(point)
    y = g_IV.GetPointY(point)
    #ov_eff = (x-float(options.Vbr))-y*1E-06*25.
    ov_eff = (x-float(options.Vbr))-y*1E-06*15.
    gain = (ov_eff+0.25)*(12.7+3.2)/1.602/0.0001
    graph_IVeff_TB.SetPoint(point,ov_eff,y/1000.)
    graph_DCR_TB.SetPoint(point,ov_eff,y*1E-06/16./gain/1.602E-19/1E09)
    print 'OV_set=%.02f   OV_eff = %.02f   I_array = %.01f    DCR = %.01f'%(x-float(options.Vbr), ov_eff, y/1000., y*1E-06/16./gain/1.602E-19/1E09)

print 'I_array at Vov_eff = 1.5 V : ', graph_IVeff_TB.Eval(1.5)
print 'I_SiPM  at Vov_eff = 1.5 V : ', graph_IVeff_TB.Eval(1.5)/16.
print 'DCR  at Vov_eff = 1.5 V : ', graph_DCR_TB.Eval(1.5)

c1 = ROOT.TCanvas('','',1300,600)
c1.Divide(2,1)
c1.cd(1)
ROOT.gPad.SetGridx()
ROOT.gPad.SetGridy()
#hPad1 = ROOT.gPad.DrawFrame(-1.5,0.,2.,50.)
hPad1 = ROOT.gPad.DrawFrame(0,0.,2.,50.)
hPad1.SetTitle(";V_{OV} [V];I [mA]")
hPad1.Draw()
graph_IVeff_TB.SetMarkerStyle(20)
graph_IVeff_TB.SetMarkerSize(1.)
graph_IVeff_TB.Draw('PL,same')
c1.cd(2)
ROOT.gPad.SetGridx()
ROOT.gPad.SetGridy()
#hPad2 = ROOT.gPad.DrawFrame(-1.5,0.,2.,50.)
hPad2 = ROOT.gPad.DrawFrame(0,0.,2.,50.)
hPad2.SetTitle(";V_{OV} [V];DCR [GHz]")
hPad2.Draw()
graph_DCR_TB.SetMarkerStyle(20)
graph_DCR_TB.SetMarkerSize(1.)
graph_DCR_TB.Draw('PL,same')

c2 = ROOT.TCanvas('','',1300,600)
c2.Divide(2,1)
c2.cd(1)
ROOT.gPad.SetGridx()
ROOT.gPad.SetGridy()
ROOT.gPad.SetLogy()
hPad1 = ROOT.gPad.DrawFrame(-1.5,0.0001,2.,100.)
hPad1.SetTitle(";V_{OV} [V];I [mA]")
hPad1.Draw()
graph_IVeff_TB.SetMarkerStyle(20)
graph_IVeff_TB.SetMarkerSize(1.)
graph_IVeff_TB.Draw('PL,same')
c2.cd(2)
ROOT.gPad.SetGridx()
ROOT.gPad.SetGridy()
ROOT.gPad.SetLogy()
hPad2 = ROOT.gPad.DrawFrame(-1.5,0.1,2.,100.)
hPad2.SetTitle(";V_{OV} [V];DCR [GHz]")
hPad2.Draw()
graph_DCR_TB.SetMarkerStyle(20)
graph_DCR_TB.SetMarkerSize(1.)
graph_DCR_TB.Draw('PL,same')

raw_input('ok?')
