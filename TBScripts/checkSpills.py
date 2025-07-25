#! /usr/bin/python

import sys
import ROOT

inFile = ROOT.TFile(sys.argv[1],"R")
data = ROOT.TTree()
data = inFile.Get("data")
n_ASIC0 = data.Draw("channelID","channelID<32","goff")
n_ASIC2 = data.Draw("channelID","channelID>=64 && channelID<96","goff")
n_ASIC3 = data.Draw("channelID","channelID>=96","goff")
print "%s   -   ASIC0: %d   ASIC2: %d   ASIC3: %d"%(sys.argv[1],n_ASIC0,n_ASIC2,n_ASIC3)

