import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '/home/cmsdaq/DAQ/tofhir/sw_daq_tofhir2b_jun22/build'))
from petsys import daqd, config
from copy import deepcopy
from time import sleep
from temperature_sensors import ltc2984_cfg_channels, ltc_read_channels

class tofhir:
    def __init__(self,configFile,trigger,aldo,l1,prescale,freq,phase,rawDataDirectory):
        #-----------------------------
        # load configuration from file
        self.mask = config.LOAD_ALL
        # if args.mode != "mixed":
        #         mask ^= config.LOAD_QDCMODE_MAP
        self.mask ^= config.LOAD_QDCMODE_MAP
        self.configFile=configFile
        self.systemConfig = config.ConfigFromFile(configFile, loadMask=self.mask)

        print("initializing daqd connection")
        self.daqd = daqd.Connection()
        self.daqd.initializeSystem()
        print("daqd initialised")
        self.systemConfig.loadToHardware(self.daqd, bias_enable=config.APPLY_BIAS_ON)
        print("loaded hardware configuration")

        self.asicsConfig = self.daqd.getAsicsConfig()
        self.activeAsics = self.daqd.getActiveAsics()

        self.rawDataDirectory = rawDataDirectory
        #--------------
        self.trigger=trigger
        self.l1=l1
        self.prescale=prescale
        self.phase=phase


#        #------------------------------------------------
#        # enable required channels (all if not specified)
#        for portID, slaveID, chipID in self.activeAsics:
#            ac = self.asicsConfig[(portID, slaveID, chipID)]
#            for channelID in range(32):
#                cc = ac.channelConfig[channelID]
#                cc.setValue("c_tgr_main", 0b11)
#
        for portID, slaveID, chipID in self.activeAsics:
            ac = self.asicsConfig[(portID, slaveID, chipID)]
            for channelID in range(32):
                cc = ac.channelConfig[channelID]
                cc.setValue("c_tgr_main", 0b00)
                if (chipID == 3 and channelID > 0) or chipID == 1:
                    cc.setValue("c_tgr_main", 0b11)
        
        if aldo:
            self.aldo=aldo
            self.hvdac_config = self.daqd.get_hvdac_config()
            for portID, slaveID, railID in self.hvdac_config.keys():
                # set 48 V as ALDO input bias (should not exceed this value)
                self.hvdac_config[(portID, slaveID, railID)] = self.systemConfig.mapBiasChannelVoltageToDAC((portID, slaveID, railID), 48)
            self.daqd.set_hvdac_config(self.hvdac_config)

        #configure temperature sensors
        ltc2984_cfg_channels(self.daqd)

    def configTrigger(self):
        # trigger modes
        if self.trigger == "none":
            print "### self-triggering mode ###"
        if self.trigger == "int":
            # Enable INTERNAL triggers from FEB/D to J15
            self.daqd.write_config_register_tgr(8, 0x21A, 0x81)
            self.daqd.setTestPulsePLL(100, int(1./(freq*6.25e-06)), phase, False)
        if self.trigger == "ext":
            # Enable EXTERNAL L1 trigger source from J15
            ext_delay = 1915 # Delay added by FPGA in 6.25 ns increments
            self.daqd.write_config_register_tgr(8, 0x21A, 0x11)
            self.daqd.write_config_register_tgr(64, 0x02A0, (1<<63) | (0<<62) | (3 << 48) | ( self.prescale << 16) | (ext_delay) ) # prescale: 0..63 -- 0 is 0%, 63 is 63/64%


        if self.trigger == "ext":
            for portID, slaveID, chipID in self.activeAsics:
                if chipID%2 is not 0:
                    continue
                gc = self.asicsConfig[(portID, slaveID, chipID)].globalConfig
                # Enable L1 trigger for even ASICs (with flex and ALDO)
                if self.l1:
                    gc.setValue("c_l1_enable", 0b01)
                else:
                    gc.setValue("c_l1_enable", 0b00)
                gc.setValue("c_l1_latency", 484) # Delay expected by ASIC in 25 ns increments

        # Use ASIC 3 channel 0 to timetag the trigger pulses
        self.asicsConfig[(0, 0, 3)].globalConfig.setValue("c_ext_tp_en", 0b1)
        self.asicsConfig[(0, 0, 3)].channelConfig[0].setValue("c_tgr_main", 0b01)
# Use ASIC 1 channel 0 to timetag the trigger pulses
#        self.asicsConfig[(0, 0, 1)].globalConfig.setValue("c_ext_tp_en", 0b1)
#        self.asicsConfig[(0, 0, 1)].channelConfig[0].setValue("c_tgr_main", 0b01)

            
    def configTOFHIR(self,vth1,vth2,vthe,delayT,delayE,attGain,fixedASIC=[],vth1_fixed=15,vth2_fixed=10,vthe_fixed=1,delayT_fixed='0b01111111',delayE_fixed='0b1111111',attGain_fixed=0):

        self.vth1=vth1
        self.vth2=vth2
        self.vthe=vthe
        self.delayT=delayT
        self.delayE=delayE
        self.attGain=attGain

        for portID, slaveID, chipID in self.activeAsics:
            if int(chipID) is 3:
                continue
            
            ac = self.asicsConfig[(portID, slaveID, chipID)]
            
            for channelID in range(32):
                cc = ac.channelConfig[int(channelID)]
                
                #cc.setValue("cfg_a3_vth_t1", vth1)
                #cc.setValue("cfg_a3_vth_t2", vth2)
                #cc.setValue("cfg_a3_vth_e", vthe)
                if (chipID == fixedASIC):
                    dac_setting_vth1 = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_t1", int(vth1_fixed))
                    dac_setting_vth2 = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_t2", int(vth2_fixed))
                    dac_setting_vthe = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_e", int(vthe_fixed))
                else:
                    dac_setting_vth1 = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_t1", int(vth1))
                    dac_setting_vth2 = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_t2", int(vth2))
                    dac_setting_vthe = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_e", int(vthe))

                # cc.setValue("cfg_a3_vth_t1", dac_setting_vth1)
                # cc.setValue("cfg_a3_vth_t2", dac_setting_vth2)
                # cc.setValue("cfg_a3_vth_e", dac_setting_vthe)
                cc.setValue("cfg_a3_ith_t1", dac_setting_vth1)
                cc.setValue("cfg_a3_ith_t2", dac_setting_vth2)
                cc.setValue("cfg_a3_ith_e", dac_setting_vthe)
                if chipID == fixedASIC:
                    cc.setValue("cfg_a2_dcr_delay_t",int(delayT_fixed,2))
                    cc.setValue("cfg_a2_dcr_delay_e",int(delayE_fixed,2))
                    cc.setValue("cfg_a2_attenuator_gain",attGain_fixed)
                #print("%d %d %d %d : %d,%d,%d") % (portID,slaveID,chipID,channelID,dac_setting_vth1,dac_setting_vth2,dac_setting_vthe)
                else:
                    cc.setValue("cfg_a2_dcr_delay_t",int(delayT,2))
                    cc.setValue("cfg_a2_dcr_delay_e",int(delayE,2))
                    cc.setValue("cfg_a2_attenuator_gain",attGain)
                
                '''
                cc.setValue("cfg_a2_attenuator_gain",0)
                cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                
                if chipID == 2 and channelID == 0:
                    cc.setValue("cfg_a2_dcr_delay_e",0b1111111)
                if chipID == 2 and channelID == 1:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 2:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 3:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 4:
                    cc.setValue("cfg_a2_dcr_delay_e",0b1111111)
                if chipID == 2 and channelID == 5:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 6:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 7:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 8:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 9:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 10:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 11:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 12:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 13:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 14:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 15:
                    cc.setValue("cfg_a2_dcr_delay_e",0b1111111)
                if chipID == 2 and channelID == 16:
                    cc.setValue("cfg_a2_dcr_delay_e",0b1111111)
                if chipID == 2 and channelID == 17:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 18:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 19:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 20:
                    cc.setValue("cfg_a2_dcr_delay_e",0b1111111)
                if chipID == 2 and channelID == 21:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 22:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 23:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 24:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 25:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 26:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 27:
                    cc.setValue("cfg_a2_dcr_delay_e",0b1111111)
                if chipID == 2 and channelID == 28:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 29:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                if chipID == 2 and channelID == 30:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0011111)
                if chipID == 2 and channelID == 31:
                    cc.setValue("cfg_a2_dcr_delay_e",0b0111111)
                '''
                
            #for ch in range(16):
            #    print "fixing channel %d" % int(ch)                                                                                                                        
            #    cc = ac.channelConfig[int(ch)]
            #    dac_setting_vth1 = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_t1", int(10))
            #    cc.setValue("cfg_a3_vth_t1", dac_setting_vth1)
            #    dac_setting_vth2 = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_t2", int(10))
            #    cc.setValue("cfg_a3_vth_t2", dac_setting_vth2)
            
            
    def configBias(self,ov,ovDrop,fixedASIC=[],ov_fixed=5,ovDrop_fixed=0):                                
        self.ov=ov
        self.ovDrop=ovDrop
        self.ovFixed=ov_fixed
        self.ovDropFixed=ovDrop_fixed

        if not self.aldo:
            biasVoltageConfig = self.daqd.get_hvdac_config()
            for key in self.daqd.getActiveBiasChannels():
                offset, prebd, bd, over__ = self.systemConfig.getBiasChannelDefaultSettings(key)
                vset = offset + bd + float(ov)
                dac_setting = self.systemConfig.mapBiasChannelVoltageToDAC(key, vset)
                biasVoltageConfig[key] = dac_setting
                self.daqd.set_hvdac_config(biasVoltageConfig)
                                
        if self.aldo:
            for portID, slaveID, chipID in self.activeAsics:
                if chipID%2 is not 0:
                    continue
                gc = (self.asicsConfig[(portID, slaveID, chipID)]).globalConfig
                gc.setValue("c_aldo_en", 0b11)
                for aldoID in ['A', 'B']:
                    bd, over__ = self.systemConfig.getBiasChannelDefaultSettingsAldo((portID, slaveID, chipID, aldoID))
                    if chipID == fixedASIC:
                        dac = self.systemConfig.mapALDOVoltageToDAC((portID, slaveID, chipID, aldoID),bd,float(ov_fixed)+float(ovDrop_fixed))
                    else:
                        dac = self.systemConfig.mapALDOVoltageToDAC((portID, slaveID, chipID, aldoID),bd,float(ov)+float(ovDrop))
                    gc.setValue("Valdo_%s_DAC"%aldoID, dac)


    def getConfigFromDaq(self):
        self.systemConfig.loadToHardware(self.daqd, bias_enable=config.APPLY_BIAS_ON)
        self.asicsConfig = self.daqd.getAsicsConfig()
        self.activeAsics = self.daqd.getActiveAsics()

    def applyConfig(self):
        cfg = deepcopy(self.asicsConfig)
        self.daqd.setAsicsConfig(cfg)
        sleep(0.05)

    def getTemperatures(self):
        temps = ltc_read_channels(self.daqd)
        return temps

    def startRun(self):
        #Turn HV ON
        print("HV ON")
        if self.aldo:
            for portID, slaveID, chipID in self.activeAsics:
                if chipID%2 is not 0:
                    continue
                gc = (self.asicsConfig[(portID, slaveID, chipID)]).globalConfig
                gc.setValue("c_aldo_en", 0b11)
            self.applyConfig()
        else:
            self.systemConfig.loadToHardware(self.daqd, bias_enable=config.APPLY_BIAS_ON)

    def openSpill(self,runName,spillNumber,tag1,tag2):
        self.daqd.openRawAcquisition(self.rawDataDirectory+"/"+runName+'/'+spillNumber)
        self.tag1=tag1
        self.tag2=tag2
#        sleep(0.1)

    def closeSpill(self):
        self.daqd.closeAcquisition()
        
    def getData(self,spillDuration):
#        self.daqd = daqd.Connection()
        self.daqd.acquire(spillDuration, self.tag1, self.tag2)
#        self.daqd.setTestPulseNone()

    def stopRun(self):
        print("HV OFF")
        #Turn HV OFF
        if self.aldo:
            for portID, slaveID, chipID in self.activeAsics:
                if chipID%2 is not 0:
                    continue
                gc = (self.asicsConfig[(portID, slaveID, chipID)]).globalConfig
                gc.setValue("c_aldo_en", 0b00)
            self.applyConfig()
        else:
            self.systemConfig.loadToHardware(self.daqd, bias_enable=config.APPLY_BIAS_OFF)

