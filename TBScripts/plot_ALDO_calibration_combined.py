#! /usr/bin/python

import ROOT
import glob
import math
import argparse
import os


asics = [0, 2]
aldos = ['A', 'B']


parser = argparse.ArgumentParser(description='merge and draw ALDO calibs')
parser.add_argument("--label", type=str, required=True, help="input folder") 
args = parser.parse_args()


aldo_graphs = []

it = 0
for asic in asics:
    for aldo in aldos:
        graph = ROOT.TGraph('../config_%s/aldo_scan_ASIC%s_ALDO%s.txt'%(args.label,asic,aldo))
        aldo_graphs.append(graph)


        
c1 = ROOT.TCanvas('c1_ALDO_Calibs', 'c1_ALDO_Calibs',1400,1000)
c1.Divide(2,2)
for i,g in enumerate(aldo_graphs):

    c1.cd(i+1)
    g.SetMarkerStyle(20)
    g.SetTitle("ASIC %s, ALDO %s; DAC; Voltage [V]"%(asics[int(i/2)], aldos[int(i%2)]))
    g.Draw("ALPE")
    ROOT.gPad.SetGrid()


c1.Print('../config_%s/c_ALDO_Calibs.png'%(args.label))
