#!/usr/bin/env python
import sys
import time
from optparse import OptionParser
from Lab5015_utils import Keithley2231A

parser = OptionParser()
parser.add_option("--power", dest="power", default="0")
parser.add_option("--target", dest="target", default="46")
(options, args) = parser.parse_args()


    
mapping = [ ['keithley2231A-0','CH1'], ['keithley2231A-0','CH2'] ]

for ch in mapping:
    mykey = Keithley2231A('ASRL/dev/'+ch[0]+'::INSTR', ch[1])
    currV = mykey.meas_V()
    print("current voltage is %.2f V") % currV
    
    if options.power == "1" and currV < 0.1:
        print("ramping up...")
        for volt in range(0,int(int(options.target)/2)+1,1):
            mykey.set_V(volt)
            mykey.set_state(1)
            time.sleep(0.2)
            I = mykey.meas_I()
            V = mykey.meas_V()
            print("v_set: %.2f V  v_meas: %.2f V  i_meas: %.3f A") %(volt,V,I)
            
    elif options.power == "0" and currV > 0.1:
        print("ramping down...")
        for volt in range(int(currV),-1,-1):
            mykey.set_V(volt)
            mykey.set_state(1)
            time.sleep(0.2)
            I = mykey.meas_I()
            V = mykey.meas_V()
            print("v_set: %.2f V  v_meas: %.2f V  i_meas: %.3f A") %(volt,V,I)
            
    else:
        print("doing nothing")
            
    time.sleep(2)
    I = mykey.meas_I()
    V = mykey.meas_V()
    print("voltage: %.2f V   current: %.3f A") %(V,I)
    

