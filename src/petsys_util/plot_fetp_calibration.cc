#include <fstream>
#include <TH1F.h>
#include <TChain.h>
#include <vector>
#include <iostream>
#include <stdio.h>
#include <assert.h>

using namespace std;


struct Event {
  long long time;
  float e;
  int id;  
} __attribute__((__packed__));

void plot_fetp_calibration(string filePrefix, int th)
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

  vector<vector<TH1F*>> hamp (0);
  vector<vector<TH1F*>> hene (0);
  vector<vector<vector<TH1F*>>> ht (0);
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




        unsigned iAsic=0;
        for (; iAsic<asic.size(); ++iAsic)
        if (asic[iAsic]==(channelID/32))
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
              50000,0,500) );
           }
         }

        hamp[iAsic][channelID%32]->Fill(step2);
        hene[iAsic][channelID%32]->Fill(energy);
        if ( step2-th >= 0 && step2-th < ht[iAsic][channelID%32].size() )
        ht[iAsic][channelID%32][step2-th]->Fill((time%640000000)/1000.);

       }

      stepBegin += readCount * sizeof(Event);

     }



   }

  delete [] buffer;

  std::ofstream fout((filePrefix+".tsv").c_str());
  fout.precision(3);

  for (unsigned iAsic=0; iAsic<asic.size(); ++iAsic) {
    for (int iCh=0; iCh<32; ++iCh) {
      if ((ht[iAsic][iCh][0]->GetEntries()<25) && (ht[iAsic][iCh][10]->GetEntries()<25)) {
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
      for (unsigned iTh=0; iTh<ht[iAsic][iCh].size(); ++iTh)
      if (ht[iAsic][iCh][iTh]->GetEntries()>25 && bestreso > ht[iAsic][iCh][iTh]->GetRMS())
      bestreso = ht[iAsic][iCh][iTh]->GetRMS();
      fout<<asic[iAsic]<<"\t"<<iCh<<"\t"<<vamp<<"\t"<<1000*bestreso<<"\t"<<enemean<<"\t"<<eneRMS<<std::endl;
     }
   }

}
