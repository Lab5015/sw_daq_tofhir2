import minimalmodbus
import serial
import pyvisa
import subprocess
import time
import sys
import zmq
from simple_pid import PID
from datetime import datetime
from TXP3510PWrapper import TXP3510P



##########################
class Keithley2231A():
    """Instrument class for Keithley 2231A

    Args:
        * portName (str): port name
        * channel (str): channel name

    """

    def __init__(self, portName='ASRL/dev/ttyUSB0::INSTR', chName="CH1"):
        print('***',portName,chName)
        self.instr = pyvisa.ResourceManager().open_resource(portName)
        self.chName = chName
        self.instr.write("SYSTem:REMote")
        self.instr.write("INST:SEL "+self.chName)

    def query(self, query):
        """Pass a query to the power supply"""
        print(self.instr.query(query).strip())

    def meas_V(self):
        """read set voltage"""
        self.instr.write("INST:SEL "+self.chName)
        volt = self.instr.query("MEAS:VOLT?").strip()
        return(float(volt))

    def meas_I(self):
        """measure current"""
        self.instr.write("INST:SEL "+self.chName)        
        curr = self.instr.query("MEAS:CURR?").strip()
        return(float(curr))
        
    def set_V(self, value):
        """set voltage"""
        return(self.instr.write("APPL "+self.chName+","+str(value)))

    def set_state(self, value):
        """Set the PS state (0: OFF, 1: RUNNING)"""
        return(self.instr.write("OUTP "+str(value)))

    def check_state(self):
        """Check the PS state (0: OFF, 1: RUNNING)"""
        return(int(self.instr.query("OUTP?").strip()))
        

##########################
class TEC():
    """class to control the SiPM temperature through the TECs
    
    Args:
        * target (str): target temp
    
    """
    
    def __init__(self, portName, target=25.): #target temperature
        self.target = float(target)
        self.portName = portName
        self.ps = TXP3510P(port=portName)
        
        self.min_voltage = 0.
        self.max_voltage = 6.
        
        self.min_temp_safe = -45.
        self.max_temp_safe = 30.
        
        self.debug = False
        
        if self.target < self.min_temp_safe or self.target > self.max_temp_safe:
            raise ValueError("### ERROR: set temp outside allowed range")
        
        self.sipm_temp = 25.
        self.I = 0.
        self.V = 0.
        self.new_voltage = self.V

        self.pid = PID(-0.2, 0., -0.7, setpoint=self.target)
        self.pid.output_limits = (-1., 1.)
    
    def power_on(self):
        print("--- powering on the PS")
        self.ps.setVoltage(0.0)
        self.ps.powerOn()
        time.sleep(2)
    
    def power_off(self):
        print("--- powering off the PS")
        self.ps.setVoltage(0.0)
        self.ps.powerOff()
        time.sleep(2)
    
    def compute_voltage(self, sipm_temp):
        
        self.sipm_temp = float(sipm_temp)

        output = self.pid(self.sipm_temp)
        self.new_voltage += output

        #safety check
        self.new_voltage = min([max([self.new_voltage,self.min_voltage]),self.max_voltage])

        if self.debug:
            I = self.ps.getCurrent()
            V = self.ps.getVoltage()
            p, i, d = self.pid.components
            #print("== DEBUG == P=", p, "I=", i, "D=", d)
            #print(self.portName,self.chName,V,I)
            #print("--- setting PS voltage to "+str(V)+"   (power "+str(I*V)+" W)    [sipm temp: "+str(self.sipm_temp)+" C]\n")
            sys.stdout.flush()

        self.ps.setVoltage(self.new_voltage)
        sleep_time = 0.1
