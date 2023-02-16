#! /usr/bin/python

import ROOT
import glob
import math
import argparse
import os


asics = [0, 2]
#asics = [0]
aldos = ['A', 'B']


def FindMaximumPoint(graph):
        value = 0.
        max = 0.
        for point in range(graph.GetN()):
                if graph.GetPointY(point) > max:
                        value = graph.GetPointX(point)
                        max = graph.GetPointY(point)
        return value


parser = argparse.ArgumentParser(description='merge and draw IV scans')
parser.add_argument("--label", type=str, required=True, help="input folder") 
args = parser.parse_args()


it = 0
for asic in asics:
    for aldo in aldos:
        ++it
        infilenames = glob.glob('../logs_%s/logIV_ASIC%d_ALDO%s*.root'%(args.label,asic,aldo))
        #print infilenames
        values = {}
        
        for infilename in infilenames:
            infile = ROOT.TFile(infilename,"READ")
            graph = infile.Get("g_IV")
            for point in range(graph.GetN()):
                if graph.GetPointX(point) not in values:
                    values[graph.GetPointX(point)] = graph.GetPointY(point)
                else:
                    values[graph.GetPointX(point)] += graph.GetPointY(point)
        
        graph_ave = ROOT.TGraph()
        xMin = 0.
        xMax = 0.
        yMax = 0.
        for v in sorted(values.keys()):
            graph_ave.SetPoint(graph_ave.GetN(),v,1.*values[v]/len(infilenames))
            yMax = 1.*values[v]/len(infilenames)
        xMin = sorted(values.keys())[0]
        xMax = sorted(values.keys())[len(values.keys())-1]
        
        c1 = ROOT.TCanvas('c1_ASIC%d_ALDO%s'%(asic,aldo),'c1_ASIC%d_ALDO%s'%(asic,aldo),1400,700)
        c1.Divide(2,1)
        c1.cd(1)
        hPad1 = ROOT.gPad.DrawFrame(xMin-0.1*(xMax-xMin),0.,xMax+0.1*(xMax-xMin),1.1*yMax)
        hPad1.SetTitle(";V_{bias} [V]; I [#muA]")
        hPad1.Draw() 
        graph_ave.SetMarkerStyle(20)
        graph_ave.SetMarkerSize(0.7)
        graph_ave.Draw("PL,same")
        
        c1.cd(2)
        hPad2 = ROOT.gPad.DrawFrame(xMin-0.1*(xMax-xMin),0.,xMax+0.1*(xMax-xMin),10.)
        hPad2.SetTitle(";V_{bias} [V]; #DeltalogI/#DeltaV [#muA/V]")
        hPad2.Draw()
        
        graph_dlogIdV = ROOT.TGraph()
        for point in range(1,graph_ave.GetN()):
            x1 = graph.GetPointX(point-1)
            y1 = graph.GetPointY(point-1)
            x2 = graph.GetPointX(point)
            y2 = graph.GetPointY(point)
            graph_dlogIdV.SetPoint(graph_dlogIdV.GetN(),0.5*(x1+x2),(math.log(y2)-math.log(y1))/(x2-x1))
        graph_dlogIdV.SetMarkerStyle(20)
        graph_dlogIdV.SetMarkerSize(0.7)
        graph_dlogIdV.Draw("PL,same")
        
        graph_dlogIdV_ave = ROOT.TGraph()
        for point in range(1,graph_dlogIdV.GetN()-1):
            x = graph_dlogIdV.GetPointX(point)
            y1 = graph_dlogIdV.GetPointY(point-1)
            y2 = graph_dlogIdV.GetPointY(point)
            y3 = graph_dlogIdV.GetPointY(point+1)
            graph_dlogIdV_ave.SetPoint(graph_dlogIdV_ave.GetN(),x,(y1+y2+y3)/3.)
        graph_dlogIdV_ave.SetLineColor(ROOT.kTeal)
        graph_dlogIdV_ave.SetLineWidth(2)
        graph_dlogIdV_ave.Draw("L,same")
        
        maximum = FindMaximumPoint(graph_dlogIdV_ave)
        fitFunc = ROOT.TF1("fitFunc","gaus(0)",xMin,xMax)
        fitFunc.SetParameter(1,maximum)
        graph_dlogIdV_ave.Fit(fitFunc,"QNRS+")
        
        xMin = maximum - fitFunc.GetParameter(2)
        xMax = maximum + fitFunc.GetParameter(2)
        fitFunc2 = ROOT.TF1("fitFunc2","gaus(0)",xMin,xMax)
        graph_dlogIdV_ave.Fit(fitFunc2,"QNRS+")
        fitFunc2.SetLineColor(ROOT.kRed)
        fitFunc2.SetLineWidth(1)
        fitFunc2.Draw("same")
        
        Vbr = fitFunc2.GetParameter(1)
        latex = ROOT.TLatex(Vbr,fitFunc2.Eval(Vbr),'V_{br.} = %.2f V'%Vbr)
        latex.SetTextFont(42)
        latex.SetTextSize(0.04)
        latex.SetTextColor(ROOT.kRed)
        latex.Draw("same")
        
        print('ASIC %d, ALDO %s:   Vbr = %.2f'%(asic,aldo,Vbr))
        c1.Print('../logs_%s/IV_ASIC%d_ALDO%s.png'%(args.label,asic,aldo))
        
        key='0       0       %d       %s'%(asic,aldo)
        VbrString='%.2f'%Vbr
        command = 'sed -i \"s%^'+key+'.*$%'+key+'        '+VbrString+'           5.00%\"'+' ../config/bias_settings_aldo.tsv'
        #print(command)
        os.system(command)
