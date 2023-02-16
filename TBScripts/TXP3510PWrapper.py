import serial
from time import sleep
from SerialClient import serialClient
class TXP3510P:
    def __init__(self,port):
        self.port=port
        if ('tcp://' in port):
            self.serial = serialClient(port)
        else:
            self.serial = serial.Serial(port, 9600,timeout=0)

        if (not 'tcp://' in self.port):
            r=self.serial.readline().strip()
        self.serial.write('*IDN?\r\n')
        sleep(0.1)
        r=self.serial.readline().strip()
        print(r)

    def getVoltage(self):
        if (not 'tcp://' in self.port):
            r=self.serial.readline().strip()
        self.serial.write('V1O?\r\n')
        sleep(0.1)
        r=self.serial.readline().strip()
        return r

    def getCurrent(self):
        if (not 'tcp://' in self.port):
            r=self.serial.readline().strip()
        self.serial.write('I1O?\r\n')
        sleep(0.1)
        r=self.serial.readline().strip()
        return r

    def getVoltageTarget(self):
        if (not 'tcp://' in self.port):
            r=self.serial.readline().strip()
        self.serial.write('V1?\r\n')
        sleep(0.1)
        r=self.serial.readline().strip()
        return r

    def getCurrentTarget(self):
        if (not 'tcp://' in self.port):
            r=self.serial.readline().strip()
        self.serial.write('I1?\r\n')
        sleep(0.1)
        r=self.serial.readline().strip()
        return r

    def setVoltage(self,value):
        print('Setting voltage to %.2f'%value)
        if (not 'tcp://' in self.port):
            r=self.serial.readline().strip()
        self.serial.write('V1 %f\r\n'%value)
        sleep(0.1)
        return r

    def setCurrent(self,value):
        print('Setting max current to %.2f'%value)
        if (not 'tcp://' in self.port):
            r=self.serial.readline().strip()
        self.serial.write('I1 %f\r\n'%value)
        sleep(0.1)
        return r

    def powerOn(self):
        if (not 'tcp://' in self.port):
            r=self.serial.readline().strip()
        self.serial.write('OP1 1\r\n')
        sleep(0.1)

    def powerOff(self):
        if (not 'tcp://' in self.port):
            r=self.serial.readline().strip()
        self.serial.write('OP1 0\r\n')
        sleep(0.1)

