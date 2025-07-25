#!/usr/bin/env python

import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2b_jun22/build'))
import logging
import threading
from temperature_sensors import ltc2984_cfg_channels, ltc_read_channels
from TEC_utils import TEC
from petsys import daqd
from time import sleep
from datetime import datetime
from optparse import OptionParser

tempChannels = {}
tempChannels[(0,'A')] = 9
tempChannels[(0,'B')] = 7
tempChannels[(2,'A')] = 17
tempChannels[(2,'B')] = 15

psChannels = {}
psChannels[(0,'A')] = '/dev/TTi-0'
psChannels[(0,'B')] = '/dev/TTi-1'

print_lock = threading.Lock()

def testThread(asic,temps,useTECs,tecs,logging):
        out = 'ASIC%d %6.2f %6.2f' % (asic,temps[tempChannels[(asic,'A')]],temps[tempChannels[(asic,'B')]])
        if str(asic) in useTECs:
                for aldo in ['A', 'B']:
                        key = (asic, aldo)
                        tecI = tecs[key].ps.getCurrent()
                        tecV = tecs[key].ps.getVoltage()
                        tecs[key].compute_voltage(temps[tempChannels[(asic,aldo)]])
                        out += '   %.2f V %.3f A'%(float(tecV[:-1]),float(tecI[:-1]))
        with print_lock:
                logging.info(out)


def main(argv):
        
        parser = OptionParser()
        parser.add_option("--run")
        parser.add_option("--targetTemp", default = -999.)
        parser.add_option("--useTECs", default = '')
        (options,args)=parser.parse_args()

	conn = daqd.Connection()
	ltc2984_cfg_channels(conn)
	
        f = open("/data1/cmsdaq/tofhir2/conf", "r")
        conf = float(f.read())
        f.close()
        
        # turn on TEC's PS
        tecs = {}
        
        logfolder = '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2b_jun22/logs_%.2f/'%conf
        if not os.path.exists(logfolder):
                os.mkdir(logfolder)
        print logfolder
        logfile = '%s/logTECs_'%logfolder+str(options.run)+'.txt'
        
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',filename=logfile,level=logging.INFO)
        
        if options.targetTemp != -999.:
                for asic in [0, 2]:
                        if str(asic) in options.useTECs:
                                for aldo in ['A', 'B']:
                                        key = (asic, aldo)
                                        usbport = psChannels[key]
                                        print(usbport)
                                        tecs[key] = TEC(usbport,options.targetTemp)
                                        tecs[key].ps.powerOn()
                                        #tecs[key].debug = True
        
        while True:
                try:
                        temps = ltc_read_channels(conn)
                        
                        threads = {}
                        for asic in [0, 2]:
                                threads[asic] = threading.Thread(target=testThread, args=(asic,temps,options.useTECs,tecs,logging))
                                threads[asic].start()
                        
                        for asic in [0, 2]:
                                threads[asic].join()
                        
                        temps = ltc_read_channels(conn)
                        
                        #temp=''
                        #cur=''
                        ##for asic in [0, 2]:
                        #for asic in [0]:
                        #        for aldo in ['A', 'B']:
                        #                key = (asic, aldo)
                        #                tecI = 0.
                        #                tecV = 0.
                        #
                        #                temps = ltc_read_channels(conn)
                        #                temp+=' %.3f'%temps[tempChannels[key]]
                        #                if options.targetTemp != -999.:
                        #                        tecI = tecs[key].ps.meas_I()
                        #                        tecV = tecs[key].ps.meas_V()
                        #                        tecs[key].compute_voltage(temps[tempChannels[key]])
                        #                        cur+= ' %.2f V %.3f A ' % (tecV,tecI)
                        #out='%s %s'%(temp,cur)
                        #
                        #logging.info(out)
                
                except KeyboardInterrupt:
                        break
                        time.sleep(3)

        if options.useTECs != '':
                print("--- powering off PS")
                for asic in [0, 2]:
                        if str(asic) in options.useTECs:
                                for aldo in ['A', 'B']:
                                        key = (asic, aldo)
                                        tecV = tecs[key].ps.setVoltage(0)
        print("bye")
        sys.exit(0)
        

if __name__ == '__main__':
	sys.exit(main(sys.argv))
