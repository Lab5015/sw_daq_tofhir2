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
#tempThreads={}
counterThreads=1

#class tempThread(threading.Thread):
#    def __init__(self, threadID, daqWrapper, out):
#        threading.Thread.__init__(self)
#        self.threadID = threadID
#        self.daqWrapper = daqWrapper
#        self.outFile=open(out,'a')
#        self.name="tempThread_%d"%threadID
#
#    def run(self):
#        try:
#            while(True):
#                temps=self.daqWrapper.getTemperatures()
#                tString=''
#                for k,t in temps.iteritems():
#                    tString+=' %.3f'%t
#                print(tString)
#                tString+='\n'
#                self.outFile.write(tString)
#                self.outFile.flush()
#                time.sleep(10)
#
#        except Exception as e:
#            print(e)
#
#    def stop(self):
#        self.join()

class daqThread(threading.Thread):
    def __init__(self, threadID, daqWrapper, run, spill, spillDuration):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.daqWrapper = daqWrapper
        self.spillDuration = spillDuration
        self.name="%d_%d"%(run,spill)   

    def run(self):
        try:
            self.daqWrapper.getData(self.spillDuration)
            self.daqWrapper.closeSpill()
        except:
            del daqThreads[self.name]

        del daqThreads[self.name]

    def stop(self):
        try:
            del daqThreads[self.name]
        except:
            print("Stopping exception")
        self.join()

def logTemperatures():
    temps=my_tofhir.getTemperatures()
    tString='{'
    for k,t in temps.iteritems():
        tString+=' %d:%.3f'%(k,t)
    print('%s }'%tString)
    tString+=' }\n'
    outFileTemperatures.write(tString)
    outFileTemperatures.flush()


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
#get fixedASIC config
fixedASIC=[]
if ('fixedASIC' in tofhirConfig):
    for v in tofhirConfig['fixedASIC'].split(','):
        fixedASIC=int(v)

fixedConfig={}
if ('fixedConfig' in tofhirConfig):
    fixedConfigValues=tofhirConfig['fixedConfig'].split(',')
    if (int(tofhirConfig['vth2_rel'])==1):
        fixedConfig={ 'vth1':str(fixedConfigValues[0]),'vth2':str(int(fixedConfigValues[0])+int(fixedConfigValues[1])),'vthe':str(fixedConfigValues[2]),'ov':str(fixedConfigValues[3]),'ovDrop':str(fixedConfigValues[4]) }
    else:
        fixedConfig={ 'vth1':str(fixedConfigValues[0]),'vth2':str(fixedConfigValues[1]),'vthe':str(fixedConfigValues[2]),'ov':str(fixedConfigValues[3]),'ovDrop':str(fixedConfigValues[4]) }

ovThSequence = config['TH_OV']    
#redefine sequence
mySequence={}
for key,value in ovThSequence.iteritems():
    values=value.split(',')
    if (int(tofhirConfig['vth2_rel'])==1):
        mySequence[str(key)]={ 'vth1':str(values[0]),'vth2':str(int(values[0])+int(values[1])),'vthe':str(values[2]),'ov':str(values[3]),'ovDrop':str(values[4]) }
    else:
        mySequence[str(key)]={ 'vth1':str(values[0]),'vth2':str(values[1]),'vthe':str(values[2]),'ov':str(values[3]),'ovDrop':str(values[4]) }
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

#    outFileTemperatures=open('testTemp.csv','a')
#    tempThreads["tempThread_0"]=tempThread(0,my_tofhir,'testTemp.csv')
#    tempThreads["tempThread_0"].start()
    sys.stderr.write("TOFHIR DAQ initialized\n")

    try:
        while True:
            ###---Post INITIALIZED status every 0.1sec (ready for start run)
            time.sleep(0.1)
            status_port.send("STATUS statuscode=%s runnumber=0 spillnumber=0 evinspill=0 paused=0" % H4DAQStatuses["INITIALIZED"])
#            logTemperatures()

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
                        mySequence[str(key)]={ 'vth1':str(values[0]),'vth2':str(values[1]),'vthe':str(values[2]),'ov':str(values[3]),'ovDrop':str(values[4]) }
                        print('Sequence ID %s:%s'%(str(key),mySequence[str(key)]))
                    sequence=sorted(ovThSequence.keys())
                    sequenceCounter=0

                    #redefine fixed ASICs
                    if ('fixedASIC' in tofhirConfig):
                        fixedASIC=tofhirConfig['fixedASIC'].split(',')
                    if ('fixedConfig' in tofhirConfig):
                        fixedConfigValues=tofhirConfig['fixedConfig'].split(',')
                        fixedConfig={ 'vth1':str(fixedConfigValues[0]),'vth2':str(fixedConfigValues[1]),'vthe':str(fixedConfigValues[2]),'ov':str(fixedConfigValues[3]),'ovDrop':str(fixedConfigValues[4]) }

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
                if ('fixedConfig' in tofhirConfig):
                    my_tofhir.configTOFHIR(mySequence[sequence[0]]['vth1'],mySequence[sequence[0]]['vth2'],mySequence[sequence[0]]['vthe'],tofhirConfig['delayT'],tofhirConfig['delayE'],tofhirConfig['attGain'],fixedASIC,fixedConfig['vth1'],fixedConfig['vth2'],fixedConfig['vthe'])
                    my_tofhir.configBias(mySequence[sequence[0]]['ov'],mySequence[sequence[0]]['ovDrop'],fixedASIC,fixedConfig['ov'],fixedConfig['ovDrop'])
                else:
                    my_tofhir.configTOFHIR(mySequence[sequence[0]]['vth1'],mySequence[sequence[0]]['vth2'],mySequence[sequence[0]]['vthe'],tofhirConfig['delayT'],tofhirConfig['delayE'],tofhirConfig['attGain'])
                    my_tofhir.configBias(mySequence[sequence[0]]['ov'],mySequence[sequence[0]]['ovDrop'])
                my_tofhir.configTrigger()
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

                        my_tofhir.openSpill(runNumber,str(spillNumber),float(mySequence[sequence[sequenceCounter]]['ov']), 10000*(int(mySequence[sequence[sequenceCounter]]['vth1'])+1)+100*(int(mySequence[sequence[sequenceCounter]]['vth2'])+1)+int(mySequence[sequence[sequenceCounter]]['vthe'])+1)

                        #---start data taking in a thread
                        #my_tofhir.applyConfig()
                        daqThreads['%d_%d'%(int(runNumber),spillNumber)]=daqThread(counterThreads,my_tofhir,int(runNumber),spillNumber,float(tofhirConfig['spillDuration']))
                        daqThreads['%d_%d'%(int(runNumber),spillNumber)].start()
                        counterThreads+=1
                        time.sleep(0.2) #---wait for DAQ to be effectively started...
                        
                        #---Inform RC that TOFPET is ready to acquire
                        cmd_port.send("DR_READY\0") 

                        #---Post READ during acquire
                        status_port.send("STATUS statuscode=%s runnumber=%s spillnumber=%s evinspill=0 paused=0" 
                                         % (H4DAQStatuses["READ"], runNumber, str(spillNumber)))

#                        my_tofhir.getData(tofhirConfig['spillDuration'])
                        time.sleep(float(tofhirConfig['spillDuration'])+0.1)

                        #--- prepare for next spill (change OV/TH if a sequence is configured)
                        if (int(tofhirConfig['nSpillsPerConfig'])>0 and (spillNumber)%int(tofhirConfig['nSpillsPerConfig'])==0 and len(sequence)>1):
                            #change threshold and OV
                            sequenceCounter=(sequenceCounter+1)%len(sequence)
                            sys.stderr.write("Changing OV/TH config to sequence ID %d\n"%sequenceCounter)

                        #--- read temperatures
#                        logTemperatures()

                        #--- re-initialise for next spill (fixes daqd connection issue on array1, should be removed in the future...)
                        #my_tofhir=tofhir(tofhirConfig['config'],tofhirConfig['trigger'],int(tofhirConfig['aldo']),int(tofhirConfig['l1']),int(tofhirConfig['prescale']),float(tofhirConfig['freq']),float(tofhirConfig['phase']),tofhirConfig['fileNamePrefix'])
                        my_tofhir.configTrigger()
                        if ('fixedConfig' in tofhirConfig):
                            my_tofhir.configTOFHIR(mySequence[sequence[sequenceCounter]]['vth1'],mySequence[sequence[sequenceCounter]]['vth2'],mySequence[sequence[sequenceCounter]]['vthe'],tofhirConfig['delayT'],tofhirConfig['delayE'],tofhirConfig['attGain'],fixedASIC,fixedConfig['vth1'],fixedConfig['vth2'],fixedConfig['vthe'])
                            my_tofhir.configBias(mySequence[sequence[sequenceCounter]]['ov'],mySequence[sequence[sequenceCounter]]['ovDrop'],fixedASIC,fixedConfig['ov'],fixedConfig['ovDrop'])
                        else:
                            my_tofhir.configTOFHIR(mySequence[sequence[sequenceCounter]]['vth1'],mySequence[sequence[sequenceCounter]]['vth2'],mySequence[sequence[sequenceCounter]]['vthe'],tofhirConfig['delayT'],tofhirConfig['delayE'],tofhirConfig['attGain'])
                            my_tofhir.configBias(mySequence[sequence[sequenceCounter]]['ov'],mySequence[sequence[sequenceCounter]]['ovDrop'])

                        my_tofhir.applyConfig()

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
                            print("---->>>> MULTITHREADINGGGG!!!!!")
                            time.sleep(0.1)
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
#            tempThreads["tempThread_0"].stop()
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
#            tempThreads["tempThread_0"].stop()
            my_tofhir.stopRun()
            sys.exit(0)
        except SystemExit:
            os._exit(0)
