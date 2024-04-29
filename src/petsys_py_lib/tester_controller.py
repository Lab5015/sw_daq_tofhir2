import daqd, tester_common
import fe_tester, bga_tester
import spi, i2c
import time

class Connection(daqd.Connection):

	def __init__(self):
		super(Connection, self).__init__()

		self.__testers = {}

	def __identify_testers(self):
			# Identify Tester Modules
			self.__testers = {}
			for portID, slaveID in self.getActiveFEBDs():
				for module in range(8):
					adc_test_result = [ spi.max111xx_check(self, portID, slaveID, 0x10 * (module+1) + chip_id) for chip_id in range(0x3, 0xA) ]

					if adc_test_result == [ False, False, False, False, False, False, False ]:
						# This port seems empty
						continue
					elif adc_test_result == [ True, True, True, True, True, True, True ]:
						# This port seems to have a FE tester
						self.__testers[(portID, slaveID, module)] = fe_tester.Tester(self, portID, slaveID, module)

					elif adc_test_result == [False, False, True, False, False, False, False]:
						# This port may have a BGA tester
						self.__testers[(portID, slaveID, module)] = bga_tester.Tester(self, portID, slaveID, module)

					else:
						print "ERROR: Unknown Tester at (%2d %2d %d): %s" % (portID, slaveID, module, adc_test_result)
						exit(1)



	def set_uut_power(self, on):
		# Always ensure controller is providing all power rails to testers
		wait_for_power = False
		for portID, slaveID in self.getActiveFEBDs():
			pwr_en = self.read_config_register(portID, slaveID, 8, 0x0213)
			if (pwr_en & 0b11) != 0b11:
				wait_for_power = True
				
			self.write_config_register(portID, slaveID, 8, 0x0213, 0b11)
				
		if wait_for_power:
			# If a FEB/D was powered off wait for a second for power to stabilize
			# and Tester FPGAs to boot
			time.sleep(1.0)

		wait_for_power = False
		for key, tester in self.get_testers().items():
				pwr_en = tester.get_uut_power()
				if pwr_en is False and on:
					wait_for_power = True
					
				tester.set_uut_power(on)
			
		if wait_for_power:
			time.sleep(1.0)

	def set_tec_power(self, on):
		for portID, slaveID in self.getActiveFEBDs():
			pwr_en =  self.read_config_register(portID, slaveID, 8, 0x0213)
			if not on:
				pwr_en &= ~0b1000
				self.write_config_register(portID, slaveID, 8, 0x0213, pwr_en)
			else:
				pwr_en |= 0b1000
				self.write_config_register(portID, slaveID, 8, 0x0213, pwr_en)
				time.sleep(0.2)

		
		


	def get_testers(self):
		if self.__testers == {}:
			self.__identify_testers()
		return self.__testers

