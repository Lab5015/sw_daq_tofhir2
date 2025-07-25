#!/usr/bin/env python

import os
import sys
import logging
import subprocess
import time
import serial
from temperature_sensors import ltc2984_cfg_channels, ltc_read_channels
from petsys import daqd
from datetime import datetime
from optparse import OptionParser
from TXP3510PWrapper import TXP3510P

tempChannels = {}
tempChannels[(0,'A')] = 9
tempChannels[(0,'B')] = 7
tempChannels[(2,'A')] = 17
tempChannels[(2,'B')] = 15


def main(argv):
        
        parser = OptionParser()
        parser.add_option("-l","--log")
        (options,args)=parser.parse_args()

	conn = daqd.Connection()
	ltc2984_cfg_channels(conn)
        
        logfolder = '/home/cmsdaq/TempLogs'
        if not os.path.exists(logfolder):
                os.mkdir(logfolder)
        print logfolder
        logfile = '%s/%s'%(logfolder,options.log)
        
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',filename=logfile,level=logging.INFO)
        
        while True:
                try:
                        logstring=''
                        for asic in [0]:
                                
                                temps = ltc_read_channels(conn)
                                #print('Aldo A: ',temps[tempChannels[(asic,'A')]])
                                #print('Aldo B: ',temps[tempChannels[(asic,'B')]])
                                logstring+='%s %s'%(temps[tempChannels[(asic,'A')]],temps[tempChannels[(asic,'B')]]) 
                                
                        out='%s'%(logstring)
                        logging.info(out)
                        time.sleep(1)
                
                except KeyboardInterrupt:
                        break
        
        time.sleep(1)
        print("bye")
        sys.exit(0)

if __name__ == '__main__':
	sys.exit(main(sys.argv))
