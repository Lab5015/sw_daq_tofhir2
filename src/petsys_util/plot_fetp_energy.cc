#include <TH1F.h>
#include <TProfile.h>
#include <TF1.h>
#include <vector>
#include <iostream>
#include <fstream>
#include <stdio.h>

using namespace std;

struct Event {
  long long time;
  float e;
  int id;  
} __attribute__((__packed__));

void plot_fetp_energy(string filePrefix, Long64_t minTime = 120e3, Long64_t maxTime = 250e3)
{
  string indexFileName = filePrefix + ".lidx";
  auto indexFile = fopen(indexFileName.c_str(), "r");
  assert (indexFile != NULL);
  
  string dataFileName = filePrefix + ".ldat";
  auto dataFile = fopen(dataFileName.c_str(), "r");
  assert (dataFile != NULL);
  
  const int BS = 100000;
  Event *buffer = new Event[BS];
  
  float step1;
  float step2;
  off_t stepBegin;
  off_t stepEnd;
  
  vector<vector<TH1*>> hamp (0);
  vector<vector<TProfile*>> hene (0);
  vector<vector<vector<TH1*>>> ht (0);
  vector<unsigned> asic (0);
  
  while (fscanf(indexFile, "%lu\t%lu\t%f\t%f\n", &stepBegin, &stepEnd, &step1, &step2) == 4) {
    if (fabs(step1-65535)>0.1 && step1>31) continue;
    
    fseek(dataFile, stepBegin, SEEK_SET);
    while(stepBegin < stepEnd) {
      int readCount = (stepEnd - stepBegin) / sizeof(Event);
      if (readCount > BS) readCount = BS;
      
      if (readCount == 0) break;
      readCount = fread(buffer, sizeof(Event), readCount, dataFile);
      assert(readCount >= 0);
      
      for(int k = 0; k < readCount; k++) {
        float energy = buffer[k].e;
        Long64_t time = buffer[k].time;
        uint channelID = buffer[k].id;
        
        
        if (energy<30 || energy>1000) continue;
        if (time%64000000<minTime || time%64000000>maxTime) continue;
        
        unsigned iAsic=0;
        for (; iAsic<asic.size(); ++iAsic)
          if (asic[iAsic]==channelID/32)
            break;
        
        if (iAsic==asic.size()) {
          // cout<<"Registering ASIC "<<channelID/32<<endl;
          asic.push_back(channelID/32);
          hene.push_back( vector<TProfile*>(0) );
          for (int iCh=0; iCh<32; ++iCh) {
            hene.back().push_back( new TProfile(Form("hene_%i",asic.back()*32+iCh),
                                                ";TP amplitude setting;energy [DAC]",
                                                32,-.5,31.5) );
          }
        }
        
        hene[iAsic][channelID%32]->Fill(step2,energy);
        
      }
      stepBegin += readCount * sizeof(Event);
    }
  }
  
  
  std::ofstream fout((filePrefix+".tsv").c_str());
  fout.precision(3);
  
  std::ofstream fout2((filePrefix+"_data.tsv").c_str());
  fout2.precision(3);
  
  for (unsigned iAsic=0; iAsic<asic.size(); ++iAsic) {
    for (unsigned iCh=0; iCh<32; ++iCh) {
      if (hene[iAsic][iCh]->GetEntries()<25) {
        fout<<asic[iAsic]<<"\t"<<iCh<<"\t0\t0"<<std::endl;
        continue;
      }
      auto lin = new TF1(Form("lin%i_%i",iAsic,iCh),"pol1",-.5,31.5);
      lin->SetParameters(-50,12);
      hene[iAsic][iCh]->Fit(lin,"QN");
      fout<<asic[iAsic]<<"\t"<<iCh<<"\t"<<lin->GetParameter(0)<<"\t"<<lin->GetParameter(1)<<std::endl;
      for (int iBin=1; iBin<=hene[iAsic][iCh]->GetNbinsX(); ++iBin)
        if (hene[iAsic][iCh]->GetBinEntries(iBin)>10)
          fout2<<asic[iAsic]<<"\t"<<iCh<<"\t"<<hene[iAsic][iCh]->GetBinCenter(iBin)<<"\t"<<hene[iAsic][iCh]->GetBinContent(iBin)<<std::endl;
    }
  }
  
}
