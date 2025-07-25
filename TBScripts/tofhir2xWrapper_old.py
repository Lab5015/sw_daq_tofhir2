from petsys import daqd, config
from copy import deepcopy
from time import sleep

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

        self.daqd = daqd.Connection()
        self.daqd.initializeSystem()

        self.asicsConfig = self.daqd.getAsicsConfig()
        self.activeAsics = self.daqd.getActiveAsics()

        self.rawDataDirectory = rawDataDirectory
        #--------------
        self.trigger=trigger
        self.l1=l1
        self.prescale=prescale
        self.phase=phase


        #------------------------------------------------
        # enable required channels (all if not specified)
        for portID, slaveID, chipID in self.activeAsics:
            ac = self.asicsConfig[(portID, slaveID, chipID)]
            for channelID in range(32):
                cc = ac.channelConfig[channelID]
                cc.setValue("c_tgr_main", 0b11)

        for portID, slaveID, chipID in self.activeAsics:
            ac = self.asicsConfig[(portID, slaveID, chipID)]
            for channelID in range(32):
                cc = ac.channelConfig[channelID]
                cc.setValue("c_tgr_main", 0b00)

        if aldo:
            self.aldo=aldo
            self.hvdac_config = self.daqd.get_hvdac_config()
            for portID, slaveID, railID in self.hvdac_config.keys():
                # set 48 V as ALDO input bias (should not exceed this value)
                self.hvdac_config[(portID, slaveID, railID)] = self.systemConfig.mapBiasChannelVoltageToDAC((portID, slaveID, railID), 48)
            self.daqd.set_hvdac_config(self.hvdac_config)

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

            
    def configTOFHIR(self,vth1,vth2,vthe,delayT,delayE,attGain):
        cfg = deepcopy(self.asicsConfig)

        self.vth1=vth1
        self.vth2=vth2
        self.vthe=vthe
        self.taps=taps
        self.attGain=attGain

        for portID, slaveID, chipID in self.activeAsics:
            ac = cfg[(portID, slaveID, chipID)]
            for channelID in range(32):
                cc = ac.channelConfig[int(channelID)]
                
                #cc.setValue("cfg_a3_vth_t1", vth1)
                #cc.setValue("cfg_a3_vth_t2", vth2)
                #cc.setValue("cfg_a3_vth_e", vthe)
                                                
                dac_setting_vth1 = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_t1", int(vth1))
                cc.setValue("cfg_a3_ith_t1", dac_setting_vth1)
                dac_setting_vth2 = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_t2", int(vth2))
                cc.setValue("cfg_a3_ith_t2", dac_setting_vth2)
                dac_setting_vthe = self.systemConfig.mapAsicChannelThresholdToDAC((portID, slaveID, chipID, channelID), "vth_e", int(vthe))
                cc.setValue("cfg_a3_ith_e", dac_setting_vthe)
                #print("%d %d %d %d : %d,%d,%d") % (portID,slaveID,chipID,channelID,dac_setting_vth1,dac_setting_vth2,dac_setting_vthe)
                                                
                cc.setValue("cfg_a2_dcr_delay_t",int(delayT,2))
                cc.setValue("cfg_a2_dcr_delay_e",int(delayE,2))
#                cc.setValue("cfg_a2_postamp_t_delay",int(taps))
                cc.setValue("cfg_a2_attenuator_gain",attGain)
                                                
        self.daqd.setAsicsConfig(cfg)
        self.asicsConfig = self.daqd.getAsicsConfig()

    def configBias(self,ov,ovDrop=0):                                
        cfg = deepcopy(self.asicsConfig)
        
        self.ov=ov
        if not self.aldo:
            biasVoltageConfig = self.daqd.get_hvdac_config()
            for key in self.daqd.getActiveBiasChannels():
                offset, prebd, bd, over__ = self.systemConfig.getBiasChannelDefaultSettings(key)
                vset = offset + bd + float(ov) + ovDrop
                dac_setting = self.systemConfig.mapBiasChannelVoltageToDAC(key, vset)
                biasVoltageConfig[key] = dac_setting
                self.daqd.set_hvdac_config(biasVoltageConfig)
                                
        if self.aldo:
            for portID, slaveID, chipID in self.activeAsics:
                if chipID%2 is not 0:
                    continue
                bd, over__ = self.systemConfig.getBiasChannelDefaultSettingsAldo((portID, slaveID, chipID))
                gc = (cfg[(portID, slaveID, chipID)]).globalConfig
                dac_A, dac_B = self.systemConfig.mapALDOVoltageToDAC((portID, slaveID, chipID),bd,float(ov))
                gc.setValue("c_aldo_en", 0b00)
                gc.setValue("Valdo_A_DAC", dac_A)
                gc.setValue("Valdo_B_DAC", dac_B)
        self.daqd.setAsicsConfig(cfg)                        
        self.asicsConfig = self.daqd.getAsicsConfig()

    def startRun(self):
        #Turn HV ON
        print("HV ON")
        if self.aldo:
            cfg = deepcopy(self.asicsConfig)
            for portID, slaveID, chipID in self.activeAsics:
                if chipID%2 is not 0:
                    continue
                gc = (cfg[(portID, slaveID, chipID)]).globalConfig
                gc.setValue("c_aldo_en", 0b11)
            self.daqd.setAsicsConfig(cfg)                        
            self.asicsConfig = self.daqd.getAsicsConfig()
        else:
            self.systemConfig.loadToHardware(self.daqd, bias_enable=config.APPLY_BIAS_ON)

    def openSpill(self,runName,spillNumber,tag1,tag2):
        self.daqd.openRawAcquisition(self.rawDataDirectory+"/"+runName+'/'+spillNumber)
        self.tag1=tag1
        self.tag2=tag2
        sleep(0.1)
        
    def getData(self,spillDuration):
#        self.daqd = daqd.Connection()
        self.daqd.acquire(spillDuration, self.tag1, self.tag2)
#        self.daqd.setTestPulseNone()

    def stopRun(self):
        print("HV OFF")
        #Turn HV OFF
        if self.aldo:
            cfg = deepcopy(self.asicsConfig)
            for portID, slaveID, chipID in self.activeAsics:
                if chipID%2 is not 0:
                    continue
                gc = (cfg[(portID, slaveID, chipID)]).globalConfig
                gc.setValue("c_aldo_en", 0b00)
            self.daqd.setAsicsConfig(cfg)                        
            self.asicsConfig = self.daqd.getAsicsConfig()
        else:
            self.systemConfig.loadToHardware(self.daqd, bias_enable=config.APPLY_BIAS_OFF)

