import minimalmodbus
import serial
import pyvisa
import subprocess
import time
import sys
from simple_pid import PID
from datetime import datetime

###################################################
class SMChiller():
    """Instrument class for SMC chiller.
    Args:
        * portname (str): port name
        * slaveaddress (int): slave address in the range 1 to 247
    """

    def __init__(self, portname='tcp://127.0.0.1:5050', slaveaddress=1):
        if 'tcp://' in portname:
            self.serial = serialClient(portname)
        else:
            print("ERROR: specify TCP address for communication")


    def read_meas_temp(self):
        """Return the measured circulating fluid discharge temperature [C]."""
        self.serial.write("read 0 1")
        return float(self.serial.readline().strip())

    def read_set_temp(self):
        """Return the circulating fluid set temperature [C]."""
        self.serial.write("read 11 1")
        return float(self.serial.readline().strip())

    def read_meas_press(self):
        """Return the measured circulating fluid discharge pressure [MPa]."""
        self.serial.write("read 2 2")
        return float(self.serial.readline().strip())

    def write_set_temp(self, value):
        """Set the working temperature [C]"""
        self.serial.write("write 11 1 "+str(value))
        return self.serial.readline().strip()

    def check_state(self):
        """Return the chiller state (0: OFF, 1: RUNNING)"""
        self.serial.write("read 12 0")
        return int(self.serial.readline().strip())

    def set_state(self, value):
        """Set the chiller state (0: OFF, 1: RUNNING)"""
        self.serial.write("write 12 0 "+str(value))
        stateFile = open("/home/cmsdaq/Programs/Lab5015Utils/chillerState.txt", "w")
        stateFile.write(str(value))
        stateFile.close()
        return self.serial.readline().strip()

###################################################
class SMChillerDirect( minimalmodbus.Instrument ):
    """Instrument class for SMC chiller.

    Args:
        * portname (str): port name
        * slaveaddress (int): slave address in the range 1 to 247

    """

    def __init__(self, portname='/dev/ttyS0', slaveaddress=1):
        minimalmodbus.Instrument.__init__(self, portname, slaveaddress)
        self.serial.baudrate = 19200
        self.serial.bytesize = 7
        self.serial.parity   = serial.PARITY_EVEN
        self.serial.timeout  = 0.3
        self.mode = minimalmodbus.MODE_ASCII


    def read_meas_temp(self):
        """Return the measured circulating fluid discharge temperature [C]."""
        return self.read_register(0, 1)

    def read_set_temp(self):
        """Return the circulating fluid set temperature [C]."""
        return self.read_register(11, 1)

    def read_meas_press(self):
        """Return the measured circulating fluid discharge pressure [MPa]."""
        return self.read_register(2, 2)

    def write_set_temp(self, value):
        """Set the working temperature [C]"""
        self.write_register(11, float(value), 1)

    def check_state(self):
        """Return the chiller state (0: OFF, 1: RUNNING)"""
        return self.read_register(12, 0)

    def set_state(self, value):
        """Set the chiller state (0: OFF, 1: RUNNING)"""
        self.write_register(12, float(value), 0)



###################################################
class PiLas():
    """Instrument class for PiLas laser

    Args:
        * portname (str): port name

    """

    def __init__(self, portname='ASRL/dev/pilas::INSTR'):
        self.instr = pyvisa.ResourceManager().open_resource(portname)
        self.instr.baud_rate = 19200
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'

    def read_tune(self):
        """Return the laser tune [%]"""
        print(self.instr.query("tune?"))

    def read_freq(self):
        """Return the laser frequency [Hz]"""
        print(self.instr.query("f?"))

    def check_state(self):
        """Return the laser state (0: OFF, 1: RUNNING)"""
        print(self.instr.query("ld?"))

    def set_state(self, value):
        """Set the laser state (0: OFF, 1: RUNNING)"""
        print(self.instr.query("ld="+str(value)))

    def set_trigger(self, value):
        """Set the laser trigger (0: int, 1: ext adj., 2: TTL)"""
        print(self.instr.query("ts="+str(value)))

    def set_tune(self, value):
        """Set the laser tune [%]"""
        print(self.instr.query("tune="+str(value)))

    def set_freq(self, value):
        """Set the laser frequency [Hz]"""
        print(self.instr.query("f="+str(value)))


##########################
class Keithley2450():
    """Instrument class for Keithley 2450

    Args:
        * portname (str): port name

    """

    def __init__(self, portname='TCPIP0::100.100.100.7::INSTR'):
        self.instr = pyvisa.ResourceManager().open_resource(portname)
        self.mybuffer = "\"defbuffer1\""
        self.instr.write(":TRAC:CLE "+self.mybuffer) #clear buffers and prepare for measure
        #self.instr.write(":SENS:FUNC \"CURR\" ") 

    def query(self, query):
        """Pass a query to the power supply"""
        print(self.instr.query(query).strip())

    def meas_V(self):
        """Return time and voltage"""
        query_out = self.instr.query(":MEASure:VOLT? "+self.mybuffer+", SEC, READ").strip()
        time = query_out.split(",")[0]
        volt = query_out.split(",")[1]
        return(float(time), float(volt))

    def meas_I(self):
        """Return time and current"""
        query_out = self.instr.query(":MEASure:CURR? "+self.mybuffer+", SEC, READ").strip()
        time = query_out.split(",")[0]
        curr = query_out.split(",")[1]
        return(float(time), float(curr))

    def meas_IV(self):
        """Return time and current"""
        self.instr.query(":MEASure:CURR? "+self.mybuffer+", READ")

        query_out = self.instr.query("FETCh? "+self.mybuffer+", SEC,READ,SOURCE").strip()
        time = query_out.split(",")[0]
        curr = query_out.split(",")[1]
        volt = query_out.split(",")[2]
        return(float(time), float(curr), float(volt))

    def set_V(self, value):
        """Set operating voltage"""
        return(self.instr.write("SOUR:VOLT "+str(value)))

    def set_state(self, value):
        """Set the PS state (0: OFF, 1: RUNNING)"""
        return(self.instr.write("OUTP "+str(value)))

    def check_state(self):
        """Check the PS state (0: OFF, 1: RUNNING)"""
        return(int(self.instr.query("OUTP?").strip()))

    def set_4wire(self, value):
        """set 4 wire mode"""
        return(self.instr.write("SENS:CURR:RSEN "+str(value)))


##########################
class Keithley2231A():
    """Instrument class for Keithley 2231A

    Args:
        * portname (str): port name
        * channel (str): channel name

    """

    def __init__(self, portname='ASRL/dev/keithley2231A::INSTR', chName="CH1"):
        self.instr = pyvisa.ResourceManager().open_resource(portname)
        self.chName = chName
        self.instr.write("SYSTem:REMote")
        self.instr.write("INST:SEL "+self.chName)

    def query(self, query):
        """Pass a query to the power supply"""
        print(self.instr.query(query).strip())

    def meas_V(self):
        """read set voltage"""
        volt = self.instr.query("MEAS:VOLT?").strip()
        return(float(volt))

    def meas_I(self):
        """measure current"""
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
class AgilentE3633A():
    """Instrument class for Agilent PS
    Args:
        * portname (str): port name
    """

    def __init__(self):
        self.instr = serial.Serial("/dev/UsbToSerial", 9600, dsrdtr=True, timeout=1)

        self.instr.write(b'SYSTem:REMote\r\n')
        self.instr.readline()
        self.instr.write(b'*CLS\r\n')
        self.instr.readline()


    def set_V(self, value):
        """set voltage"""
        cmdString = "APPL "+str(value)+"\r\n"
        self.instr.write(str.encode(cmdString))
        self.instr.readline()
        return

    def meas_I(self):
        """measure current"""
        cmdString = "MEAS:CURR?\r\n"
        self.instr.write(cmdString.encode())
        curr = self.instr.readline()
        return(float(curr))

    def meas_V(self):
        """measure tension"""
        cmdString = "MEAS:VOLT?\r\n"
        self.instr.write(cmdString.encode())
        curr = self.instr.readline()
        return(float(curr))

    def set_state(self, value):
        """Set the PS state (0: OFF, 1: RUNNING)"""
        cmdString = "OUTP "+ str(value)+"\r\n"
        self.instr.write(cmdString.encode())
        out = self.instr.readline()
        return

    def set_range(self, value):
        """Set the PS voltage range (LOW, HIGH)"""
        cmdString = "VOLT:RANG "+ str(value)+"\r\n"
        self.instr.write(cmdString.encode())
        out = self.instr.readline()
        return
        
    def check_state(self):
        """Check the PS state (0: OFF, 1: RUNNING)"""
        cmdString = "OUTP?\r\n"
        self.instr.write(cmdString.encode())
        state = self.instr.readline()
        return(int(state.decode()))




##########################
class sipmPower():
    """class to control the power delivered to SiPMs

    Args:
        * target (str): target power

    """

    def __init__(self, target=0.432): #target in Watts
        self.target = float(target)
        self.sipm = Keithley2231A(chName="CH1")

        self.min_voltage = 0.
        self.max_voltage = 2.

        self.min_pow_safe = 0.
        self.max_pow_safe = 2. # Watts

        self.debug = True

        if self.target < self.min_pow_safe or self.target > self.max_pow_safe:
            raise ValueError("### ERROR: set power outside allowed range")

        self.state = self.sipm.check_state()
        self.I = 0.
        self.V = 0.
        self.P = 0.
        self.new_voltage = self.V

        self.pid = PID(0.5, 0., 1., setpoint=self.target)
        self.pid.output_limits = (-0.5, 0.5)


    def power_on(self):
        if self.state is 0:
            print("--- powering on the PS")
            self.sipm.set_V(0.0)
            self.sipm.set_state(1)
            time.sleep(2)
            self.state = self.sipm.check_state()
            if self.state == 0:
                raise ValueError("### ERROR: PS did not power on")

    def power_off(self):
        if self.state is 1:
            print("--- powering off the PS")
            self.sipm.set_V(0.0)
            self.sipm.set_state(0)
            time.sleep(2)
            self.state = self.sipm.check_state()
            if self.state != 0:
                raise ValueError("### ERROR: PS did not power off")

    def compute_voltage(self, I, V):
        self.power_on()

        self.I = I
        self.V = V
        self.P = self.I * self.V - (self.I * self.I * 1.2) # hardcoded resistance of the cable
        output = self.pid(self.P)
        self.new_voltage += output

        #safety check
        self.new_voltage = min([max([self.new_voltage,self.min_voltage]),self.max_voltage])

        if self.debug:
            print(datetime.now())
            p, i, d = self.pid.components
            print("== DEBUG == P=", p, "I=", i, "D=", d)
            print("--- setting SiPM voltage to "+str(self.new_voltage)+" V    [sipm current: "+str(self.I)+" sipm power: "+str(self.P)+" W]\n")
            sys.stdout.flush()

        self.sipm.set_V(self.new_voltage)
        sleep_time = 0.5

##########################
class sipmTemp():
    """class to control the SiPM temperature

    Args:
        * target (str): target temp

    """

    def __init__(self, target=25): # target in C
        self.target = float(target)
        self.TEC = Keithley2450()

        self.min_voltage = -5.
        self.max_voltage = 5.

        self.min_temp_safe = -35.
        self.max_temp_safe = 40.

        self.debug = True

        if self.target < self.min_temp_safe or self.target > self.max_temp_safe:
            raise ValueError("### ERROR: set temp outside allowed range")

        self.state = self.TEC.check_state()
        self.sipm_temp = 25.
        self.I = 0.
        self.V = 0.
        self.new_voltage = self.V

        self.pid = PID(-0.25, 0., -1., setpoint=self.target)
        self.pid.output_limits = (-2., 2.)


    def power_on(self):
        if self.state is 0:
            print("--- powering on the PS")
            self.TEC.set_V(0.0)
            self.TEC.set_state(1)
            time.sleep(2)
            self.state = self.TEC.check_state()
            if self.state == 0:
                raise ValueError("### ERROR: PS did not power on")

    def power_off(self):
        if self.state is 1:
            print("--- powering off the PS")
            self.TEC.set_V(0.0)
            self.TEC.set_state(0)
            time.sleep(2)
            self.state = self.TEC.check_state()
            if self.state != 0:
                raise ValueError("### ERROR: PS did not power off")


    def compute_voltage(self, sipm_temp):
        self.power_on()

        self.sipm_temp = float(sipm_temp)

        output = self.pid(self.sipm_temp)
        self.new_voltage += output

        #safety check
        self.new_voltage = min([max([self.new_voltage,self.min_voltage]),self.max_voltage])

        if self.debug:
            (date, I, V) = self.TEC.meas_IV()
            print(date)
            p, i, d = self.pid.components
            print("== DEBUG == P=", p, "I=", i, "D=", d)
            print("--- setting TEC power to "+str(I*V)+" W    [sipm temp: "+str(self.sipm_temp)+" C]\n")
            sys.stdout.flush()

        self.TEC.set_V(self.new_voltage)
        sleep_time = 0.5


##########################
class movingTable():
    """Instrument class for controlling the movingTable
    Args:
        * portname (str): port name
    """

    def __init__(self, portname='/dev/cu.usbserial-146110'):
        self.instr = serial.Serial(portname, 115200)
        # Wake up grbl
        wakeUp = "\r\n\r\n"
        self.instr.write(wakeUp.encode())
        time.sleep(2)  # Wait for grbl to initialize
        self.instr.flushInput()  # Flush startup text in serial input
        self.globalX = 0.0
        self.globalY = 0.0
        self.absMaxX = 151
        self.absMaxY = 151

    #go home when done
    def __del__(self):
        self.goHome()

    def isSafe(self):
        if abs(self.globalX) < self.absMaxX and abs(self.globalY) < self.absMaxY:
            return 0
        else:
            self.goHome()
            print("COORDINATEDS OUT OF RANGE")
            sys.exit()

    def deltaX(self, delta):
        self.globalX += delta
        self.isSafe()
        command = "G90 G0 X"+str(self.globalX)+" Y"+str(self.globalY)+"\n"
        self.instr.write(command.encode()) # Send g-code block to grbl
        grbl_out = self.instr.readline()

    def deltaY(self, delta):
        self.globalY += delta
        self.isSafe()
        command = "G90 G0 X"+str(self.globalX)+" Y"+str(self.globalY)+"\n"
        self.instr.write(command.encode()) # Send g-code block to grbl
        grbl_out = self.instr.readline()

    def deltaXY(self, deltaX, deltaY):
        self.globalX += deltaX
        self.globalY += deltaY
        self.isSafe()
        command = "G90 G0 X"+str(self.globalX)+" Y"+str(self.globalY)+"\n"
        self.instr.write(command.encode()) # Send g-code block to grbl
        grbl_out = self.instr.readline()

    def getGlobalCoordinates(self):
        return self.globalX, self.globalY

    def goHome(self):
        self.globalX = 0.0
        self.globalY = 0.0
        command = "G90 G0 X"+str(self.globalX)+" Y"+str(self.globalY)+"\n"
        self.instr.write(command.encode()) # Send g-code block to grbl
        grbl_out = self.instr.readline()


##########################
def read_box_temp():
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    out = subprocess.run(['ssh', 'pi@100.100.100.5', './getTemperature.py ', current_time],
                         stdout=subprocess.PIPE)
    result = out.stdout.decode('utf-8').rstrip('\n').split()

    if len(result) != 2:
        raise ValueError("Could not read box temperature")
    else:
        return result[1]


##########################
def read_arduino_temp():
    command = '1'
    out = ""

    try:
        ser = serial.Serial("/dev/ttyACM0", 115200)
        ser.timeout = 1
    except serial.serialutil.SerialException:
        print('not possible to establish connection with device')

    data = ser.readline()[:-2] #the last bit gets rid of the new-line chars
    x = ser.write((command+'\r\n').encode())

    # let's wait one second before reading output (let's give device time to answer)
    time.sleep(1)
    while ser.inWaiting() > 0:
        out += ser.read(1).decode()

    ser.close()

    if out != "":
        out.replace("\r","").replace("\n","")

    result = out.rstrip('\n').split()
    if len(result) != 7:
        raise ValueError("Could not read arduino temperature")
    else:
        airTemp = float(result[6])
        if airTemp < 0:
            result[6] = str(-airTemp - 3276.80)
        return result
