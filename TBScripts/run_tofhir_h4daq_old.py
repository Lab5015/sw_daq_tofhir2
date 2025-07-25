#!/bin/python

###---H4DAQ statuses
H4DAQStatuses = {
    "START" 	   : 0,
    "INIT" 	   : 1,
    "INITIALIZED"  : 2,
    "BEGINSPILL"   : 3,
    "CLEARED" 	   : 4,
    "WAITFORREADY" : 5,
    "CLEARBUSY"    : 6,
    "WAITTRIG" 	   : 7,
    "READ"     	   : 8,
    "ENDSPILL"	   : 9,
    "RECVBUFFER"   : 10,
    "SENTBUFFER"   : 11,
    "SPILLCOMPLETED": 12,
    "BYE"	   : 13,
    "ERROR"	   : 14
}

import zmq 
import time
import sys
import datetime
from copy import deepcopy
import argparse
import commands
import os
import threading


from tofhir2xWrapper import tofhir

daqThreads={}
counterThreads=1

class daqThread (threading.Thread):
    def __init__(self, threadID, daqWrapper, run, spill, spillDuration):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.daqWrapper = daqWrapper
        self.spillDuration = spillDuration
        self.name= "%d_%d"%(run,spill)   
    def run(self):
        try:
            self.daqWrapper.getData(self.spillDuration)
        except:
            del daqThreads[self.name]

        del daqThreads[self.name]

parser = argparse.ArgumentParser(description='Acquire SiPM data')
parser.add_argument("--config", type=str, required=True, help="Configuration file")
#------------------------
# parsing input arguments
args = parser.parse_args()

import configparser
config = configparser.ConfigParser()
print("Reading config from %s"%args.config)
config.read(args.config)
daqConfig = config['H4DAQ']
tofhirConfig = config['TOFHIR']
ovThSequence = config['TH_OV']
    
#redefine sequence
mySequence={}
for key,value in ovThSequence.iteritems():
    values=value.split(',')
    mySequence[str(key)]={ 'vth1':str(values[0]),'vth2':str(values[1]),'vthe':str(values[2]),'ov':str(values[3]) }
    print('Sequence ID %s:%s'%(str(key),mySequence[str(key)]))
sequence=sorted(ovThSequence.keys())
sequenceCounter=0

# MAIN LOOP
if __name__ == "__main__":
    ###---setup ZMQ network
    context = zmq.Context()
    poller = zmq.Poller()
    #---connect to other daemons ports
    sockets = {}
    sockets["GUI"] = context.socket(zmq.SUB)
    print("Connecting GUI at %s"%daqConfig["GUI_port"])
    sockets["GUI"].connect(daqConfig["GUI_port"])
    sockets["GUI"].setsockopt(zmq.SUBSCRIBE, '')
    poller.register(sockets["GUI"], zmq.POLLIN)
    sockets["RC"] = context.socket(zmq.SUB)
    print("Connecting RC at %s"%daqConfig["RC_port"])
    sockets["RC"].connect(daqConfig["RC_port"])
    sockets["RC"].setsockopt(zmq.SUBSCRIBE, '')
    poller.register(sockets["RC"], zmq.POLLIN)
    #---Public status_port
    status_port = context.socket(zmq.PUB)
    print("Publishing STATUS at %s"%daqConfig["STATUS_port"])
    status_port.bind('tcp://*:%s' % daqConfig["STATUS_port"])    
    #---Public commandport
    cmd_port = context.socket(zmq.PUB)
    print("Publishing CMD at %s"%daqConfig["CMD_port"])
    cmd_port.bind('tcp://*:%s' % daqConfig["CMD_port"])    

    
    #init tofhir
    my_tofhir=tofhir(tofhirConfig['config'],tofhirConfig['trigger'],int(tofhirConfig['aldo']),int(tofhirConfig['l1']),int(tofhirConfig['prescale']),float(tofhirConfig['freq']),float(tofhirConfig['phase']),tofhirConfig['fileNamePrefix'])
    my_tofhir.configTrigger()
    sys.stderr.write("TOFHIR DAQ initialized\n")

    try:
        while True:
            ###---Post INITIALIZED status every 0.1sec (ready for start run)
            time.sleep(0.1)
            status_port.send("STATUS statuscode=%s runnumber=0 spillnumber=0 evinspill=0 paused=0" % H4DAQStatuses["INITIALIZED"])

            ###---check for GUI commands
            ###   do not wait since we need to continue publish data
            try:
                message = sockets["GUI"].recv(zmq.DONTWAIT)            

                ###---Handle GUI_DIE (after pressing "Quit DAQ" button in GUI)
                ###   kill daqd instance and exit 
                if "GUI_DIE" in message:
                    sys.stderr.write(message+'\n')
                    status_port.send("STATUS statuscode=%s runnumber=0 spillnumber=0 evinspill=0 paused=0" % H4DAQStatuses["BYE"])
                    my_tofhir.stopRun()
                    #                commands.getoutput("sudo systemctl stop daqd.service")
                    sys.exit(0)

                ###---reconfigure asic if GUI send new configuration
                if "GUI_RECONFIG" in message:
                    sys.stderr.write(message+'\n')
                    print("Reading config from %s"%args.config)
                    config.read(args.config)
                    daqConfig = config['H4DAQ']
                    tofhirConfig = config['TOFHIR']
                    ovThSequence = config['TH_OV']
    
                    #redefine sequence
                    mySequence={}
                    for key,value in ovThSequence.iteritems():
                        values=value.split(',')
                        mySequence[str(key)]={ 'vth1':str(values[0]),'vth2':str(values[1]),'vthe':str(values[2]),'ov':str(values[3]) }
                        print('Sequence ID %s:%s'%(str(key),mySequence[str(key)]))
                    sequence=sorted(ovThSequence.keys())
                    sequenceCounter=0

                    #update some tofhir parameters (not all of them)
                    my_tofhir.trigger=tofhirConfig['trigger']
                    my_tofhir.l1=int(tofhirConfig['l1'])
                    my_tofhir.prescale=int(tofhirConfig['prescale'])
                    my_tofhir.freq=float(tofhirConfig['freq'])
                    my_tofhir.phase=float(tofhirConfig['phase'])
            
                ###---wait for STARTRUN from GUI
                if "GUI_STARTRUN" not in message:
                    continue
                sys.stderr.write(message+'\n')
                runNumber = message.split()[1]
                spillNumber = 0
                commands.getoutput("mkdir -p %s/%s" % (tofhirConfig['fileNamePrefix'], runNumber))

                ###---FIXME -> ASIC config CHECK how to close connection with daqd
                my_tofhir.configTOFHIR(mySequence[sequence[0]]['vth1'],mySequence[sequence[0]]['vth2'],mySequence[sequence[0]]['vthe'],tofhirConfig['delayT'],,tofhirConfig['delayE'],tofhirConfig['attGain'])
                my_tofhir.configBias(mySequence[sequence[0]]['ov'],mySequence[sequence[0]]['ovDrop'])
                if (len(sequence)>1):
                    sequenceCounter=(sequenceCounter+1)%len(sequence)
                my_tofhir.startRun()

            except zmq.Again:
                continue

            ###---Spill loop (during run)
            timeCounter = 0
            while True:
                time.sleep(0.001)
                timeCounter = timeCounter+1
                if timeCounter == 200:
                    timeCounter = 0
                    status_port.send("STATUS statuscode=%s runnumber=%s spillnumber=%s evinspill=0 paused=0" 
                                     % (H4DAQStatuses["CLEARED"], runNumber, str(spillNumber)))

                try:
                    message = sockets["RC"].recv(zmq.DONTWAIT)
                    sys.stderr.write("Spill loop message: %s\n" % message)
                    if message == "WE\0":
                        sys.stderr.write("Begin spill\n")
                        spillNumber = spillNumber+1

                        #---wait for other spill threads to be completed (should not happen...)
                        while(len(daqThreads)>0):
                            time.sleep(0.01)


                        my_tofhir.configTrigger()
                        my_tofhir.openSpill(runNumber,str(spillNumber),float(mySequence[sequence[sequenceCounter]]['ov']), 10000*(int(mySequence[sequence[sequenceCounter]]['vth1'])+1)+100*(int(mySequence[sequence[sequenceCounter]]['vth2'])+1)+int(mySequence[sequence[sequenceCounter]]['vthe'])+1)

                        #---start data taking in a thread
                        daqThreads['%d_%d'%(int(runNumber),spillNumber)]=daqThread(counterThreads,my_tofhir,int(runNumber),spillNumber,float(tofhirConfig['spillDuration']))
                        daqThreads['%d_%d'%(int(runNumber),spillNumber)].start()
                        counterThreads+=1
                        time.sleep(0.15) #---wait for DAQ to be effectively started...
                        
                        #---Inform RC that TOFPET is ready to acquire
                        cmd_port.send("DR_READY\0") 

                        #---Post READ during acquire
                        status_port.send("STATUS statuscode=%s runnumber=%s spillnumber=%s evinspill=0 paused=0" 
                                         % (H4DAQStatuses["READ"], runNumber, str(spillNumber)))

#                        my_tofhir.getData(tofhirConfig['spillDuration'])
                        time.sleep(float(tofhirConfig['spillDuration']))

                        #--- prepare for next spill (change OV/TH if a sequence is configured)
                        if (int(tofhirConfig['nSpillsPerConfig'])>0 and (spillNumber)%int(tofhirConfig['nSpillsPerConfig'])==0 and len(sequence)>1):
                            #change threshold and OV
                            sys.stderr.write("Changing OV/TH config to sequence ID %d\n"%sequenceCounter)
                            my_tofhir.configTOFHIR(mySequence[sequence[sequenceCounter]]['vth1'],mySequence[sequence[sequenceCounter]]['vth2'],mySequence[sequence[sequenceCounter]]['vthe'],tofhirConfig['taps'],tofhirConfig['attGain'])
                            my_tofhir.configBias(mySequence[sequence[sequenceCounter]]['ov'])
                            sequenceCounter=(sequenceCounter+1)%len(sequence)

                        try:
                            post_acq_message = sockets["RC"].recv(zmq.DONTWAIT)
                            if post_acq_message == "EE\0":
                                sys.stderr.write("End spill\n")
                                status_port.send("STATUS statuscode=%s runnumber=%s spillnumber=%s evinspill=0 paused=0" 
                                          % (H4DAQStatuses["ENDSPILL"], runNumber, str(spillNumber)))
                                ###---FIXME -> dump raw data to root file
                            else:
                                sys.stderr.write("ERROR: EE expected from RC got %s\n" % post_acq_message)
                                status_port.send("STATUS statuscode=%s runnumber=%s spillnumber=%s evinspill=0 paused=0" 
                                                 % (H4DAQStatuses["ERROR"], runNumber, str(spillNumber)))
                        except zmq.Again:
                            sys.stderr.write("ERROR: EE expected from RC got nothing\n")
                            status_port.send("STATUS statuscode=%s runnumber=%s spillnumber=%s evinspill=0 paused=0" 
                                             % (H4DAQStatuses["ERROR"], runNumber, str(spillNumber)))
                            continue
                    
                    ###---if RC sent ENDRUN exit
                    if message == "ENDRUN\0":
                        #Wait for daqThreads to be finished
                        while(len(daqThreads)>0):
                            time.sleep(0.01)
                        sys.stderr.write("Run ended\n")
                        my_tofhir.stopRun()
                        break
            
                except zmq.Again:
                    continue


    except KeyboardInterrupt:
        print('Interrupted')
        #Wait for daqThreads to be finished
        while(len(daqThreads)>0):
            time.sleep(0.01)
        try:
            my_tofhir.stopRun()
            sys.exit(0)
        except SystemExit:
            os._exit(0)


    except Exception as e:
        print('General Exception')
        print(e)
        #Wait for daqThreads to be finished
        while(len(daqThreads)>0):
            time.sleep(0.01)
        try:
            my_tofhir.stopRun()
            sys.exit(0)
        except SystemExit:
            os._exit(0)
