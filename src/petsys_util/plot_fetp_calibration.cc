#include <fstream>
#include <TH1F.h>
#include <TChain.h>
#include <vector>
#include <iostream>

using namespace std;

void plot_fetp_calibration(string filePrefix, int th)
{
  auto data = new TChain("data","data");
  data->Add((filePrefix+".root").c_str());

  float step1, step2, tot, energy;
  Long64_t time;
  uint channelID;
  data->SetBranchAddress("step1",&step1);
  data->SetBranchAddress("step2",&step2);
  data->SetBranchAddress("time",&time);
  data->SetBranchAddress("energy",&energy);
  data->SetBranchAddress("channelID",&channelID);

  vector<vector<TH1F*>> hamp (0);
  vector<vector<TH1F*>> hene (0);
  vector<vector<vector<TH1F*>>> ht (0);
  vector<int> asic (0);

  for (int iEv=0; iEv<data->GetEntries(); ++iEv) {
    data->GetEntry(iEv);

    if (fabs(step1-65535)>0.1 && step1>31) continue;

    int iAsic=0;
    for (; iAsic<asic.size(); ++iAsic)
      if (asic[iAsic]==channelID/32)
	break;

    if (iAsic==asic.size()) {
      asic.push_back(channelID/32);
      hamp.push_back( vector<TH1F*>(0) );
      hene.push_back( vector<TH1F*>(0) );
      ht.push_back( vector<vector<TH1F*>>(0) );
      for (int iCh=0; iCh<32; ++iCh) {
	hamp.back().push_back( new TH1F(Form("hamp_%i",asic.back()*32+iCh),
					";threshold [DAC]",
					64,-.5,63.5) );
	hene.back().push_back( new TH1F(Form("hene_%i",asic.back()*32+iCh),
					";energy [DAC]",
					950,49.5,999.5) );
	ht.back().push_back( vector<TH1F*>(0) );
	for (int iTh=0; iTh<16; ++iTh)
	  ht.back().back().push_back( new TH1F(Form("ht_%i_%i",asic.back()*32+iCh,iTh),
					       ";ToA [ns]",
					       8000,120,200) );
      }
    }

    hamp[iAsic][channelID%32]->Fill(step2);
    hene[iAsic][channelID%32]->Fill(energy);
    if ( step2-th >= 0 && step2-th < ht[iAsic][channelID%32].size() )
      ht[iAsic][channelID%32][step2-th]->Fill((time%10000000)/1000.);

  }

  std::ofstream fout((filePrefix+".tsv").c_str());
  fout.precision(3);

  for (int iAsic=0; iAsic<asic.size(); ++iAsic) {
    for (int iCh=0; iCh<32; ++iCh) {
      if (ht[iAsic][iCh][0]->GetEntries()<25) {
	fout<<asic[iAsic]<<"\t"<<iCh<<"\t0\t0\t0\t0"<<std::endl;
	continue;
      }
      float vamp = 0;
      float target = 0.5*hamp[iAsic][iCh]->GetBinContent(th+1);
      for (int iBin=hamp[iAsic][iCh]->GetNbinsX(); iBin>0; --iBin)
	if (hamp[iAsic][iCh]->GetBinContent(iBin)>target) {
	  float dNlow = hamp[iAsic][iCh]->GetBinContent(iBin)-target;
	  float dNhig = target-hamp[iAsic][iCh]->GetBinContent(iBin+1);
	  vamp = 1.25 * (hamp[iAsic][iCh]->GetBinCenter(iBin) + dNlow / (dNlow+dNhig));
	  break;
	}
      float enemean = hene[iAsic][iCh]->GetMean();
      float eneRMS = hene[iAsic][iCh]->GetRMS();
      float bestreso = 999;
      for (int iTh=0; iTh<ht[iAsic][iCh].size(); ++iTh)
	if (ht[iAsic][iCh][iTh]->GetEntries()>25 && bestreso > ht[iAsic][iCh][iTh]->GetRMS())
	  bestreso = ht[iAsic][iCh][iTh]->GetRMS();
      fout<<asic[iAsic]<<"\t"<<iCh<<"\t"<<vamp<<"\t"<<1000*bestreso<<"\t"<<enemean<<"\t"<<eneRMS<<std::endl;
    }
  }

}
