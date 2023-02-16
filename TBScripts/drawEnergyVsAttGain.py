#! /usr/bin/python

import ROOT

runs = {}
'''
runs[7] = 4229
runs[6] = 4230
runs[5] = 4231
runs[4] = 4232
runs[3] = 4233
runs[2] = 4234
runs[1] = 4235
'''

#runs[7] = 4236
#runs[6] = 4238
runs[5] = 4240
#runs[4] = 4242
#runs[3] = 4243
#runs[2] = 4244
#runs[1] = 4245

channels = [64,65,66,67,68,69,70]

c = ROOT.TCanvas("c","c")
hPad = ROOT.gPad.DrawFrame(0.,0.0001,1024.,0.1)
hPad.SetTitle(";energy [ADC];event fraction")
hPad.Draw()
ROOT.gPad.SetGridx()
ROOT.gPad.SetGridy()
ROOT.gPad.SetLogy()

histos = {}
infiles = {}
trees = {}

colorIt = 0

for it in runs:
    attGain = it
    run = runs[it]
    
    infiles[it] = ROOT.TFile("/data/tofhir2/h8/reco/%d/1_e.root"%run,"READ")
    trees[it] = infiles[it].Get("data")
    for ch in channels:
        histos[(it,ch)] = ROOT.TH1F("histo_attGain%d_ch%d"%(attGain,ch),"",256,0.,1024.)
        trees[it].Draw("energy[channelIdx[%d]]>>histo_attGain%d_ch%d"%(ch,attGain,ch),"channelIdx[%d]>=0"%ch,"goff")
        histos[(it,ch)].Scale(1./histos[(it,ch)].Integral())
        histos[(it,ch)].SetLineColor(ROOT.kBlack+colorIt)
        histos[(it,ch)].SetLineWidth(2)
        c.cd()
        histos[(it,ch)].Draw("hist,same")
        colorIt += 1
        
c.Print("energyVsAttGain.png")
