from . import tofhir2, tofhir2b, config
import sys, os, tempfile, time
import numpy as np
import pandas as pd
from copy import deepcopy
import bitarray
import itertools

def fe_check_current(conn, ts, ILOW, IHIGH, when, fname):
	results = {}
	f = open(fname, "w")
	for m,t in ts:
		iin = t.get_uut_iin()
		f.write("%d\t%f\n" % (m,iin))
		if iin < ILOW:
			results[m] = [ "UUT CURRENT %s TOO LOW (%5.3f A)" % (when,iin) ]

		elif iin > IHIGH:
			results[m] = [ "UUT CURRENT %s TOO HIGH (%5.3f A)" % (when, iin) ]
	f.close()
	return results

def bga_check_current(conn, sockets, ILOW, IHIGH, when, fname):
	print "BGA CHECK CURRENT"
	results = {}
	f = open(fname, "w")
	for m, a, t in sockets:
		iin = t.get_uut_iin(a)
		f.write("%d\t%d\t%f\n" % (m, a, iin))
		
		if iin < ILOW:
			results[m,a] = [ "UUT CURRENT %s TOO LOW (%5.3f A)" % (when,iin) ]

		elif iin > IHIGH:
			results[m,a] = [ "UUT CURRENT %s TOO HIGH (%5.3f A)" % (when,iin) ]

	f.close()
	return results
	
def bga_check_reset_n(conn, sockets):
	print "BGA CHECK RESET"
	results = {}
	
	for m,a,t in sockets:
		t.set_uut_reset_n(a, 0)
		
	conn.initializeSystem()
	asicsConfig = conn.getAsicsConfig()
	
	for m,a,t in sockets:
		if (0,0,2*m+a) in asicsConfig.keys():
			results[m,a] = [ "RESET_N FAIL" ]

	for m,a,t in sockets:
		t.set_uut_reset_n(a, 1)

	return results
	

def check_asic_communication(conn, sockets):
	print "CHECK ASIC COMMUNICATION"
	results = {}
	conn.initializeSystem()
	asicsConfig = conn.getAsicsConfig()
	for m,a,t in sockets:
		if (0,0,2*m+a) not in asicsConfig.keys():
			results[m,a] = [ "NO COMMUNICATION" ]

	return results

def bga_do_bg_trim(conn, sockets):
	print "DO BG TRIM"
	TRIM_OPTIONS = { 
		7       : -12.28E-3,
		6       : -12.32E-3,
		5       : -12.34E-3,
		4       : +19.27E-3,
		3       : +9.73E-3,
		2       : +4.89E-3,
		1       : +2.49E-3,
		0       : +1.25E-3,
		None    : 0
	}

	target = 0.300

	for m,a,t in sockets:
		t.set_uut_vfuse(True)
	time.sleep(0.1)
	
	
	for m,a,t in sockets:
		
		busID = m
		chipID = a
		readID = 2*m + a
		
		current_trim_options = deepcopy(TRIM_OPTIONS)

		value = t.get_uut_vbg(a)
		while abs(value - target) > 1E-3:
			selected_option = None
			expected_voltage = value + 1E6
			selected_option_error = abs(value - target)
			
			for option, delta in current_trim_options.items():

				# If current value is above target + 4 mV, consider only negative trim options
				if (value > (target + 4e-3)) and (delta >= 0): continue
				
				option_error = abs(value + delta - target)
				if option_error < selected_option_error:
					selected_option_error = option_error
					selected_option = option
					expected_voltage = value + delta
			
			if selected_option is None: break
			
			gc = tofhir2b.AsicGlobalConfig()
			gc.setValue("EFUSE_A", selected_option)
			conn._Connection__tofhir2_cmd(0, 0, busID, chipID, readID, 32, True, False, gc)              
			
			del current_trim_options[selected_option]
			
			
			# Trim
			conn._Connection__tofhir2_cmd(0, 0, busID, chipID, readID, 37, True, False, bitarray.bitarray(160))
			time.sleep(0.1)
			
			# Load
			conn._Connection__tofhir2_cmd(0, 0, busID, chipID, readID, 35, True, False, bitarray.bitarray(254))
			time.sleep(0.1)
			conn._Connection__tofhir2_cmd(0, 0, busID, chipID, readID, 36, True, False, bitarray.bitarray(254))
			time.sleep(0.1)

			value = t.get_uut_vbg(a)

	for m,a,t in sockets:
		t.set_uut_vfuse(False)
	


def bga_check_bg_trim(conn, sockets, fname):
	print "CHECK BG TRIM"
	results = {}
	f = open(fname, "w")
	for m,a,t in sockets:
		v = t.get_uut_vbg(a)
		f.write("%d\t%d\t%f\n" % (m, a, v))
		if abs(v - 0.300) > 6E-3:
			results[m,a] = [ "BANDGAP %5.3f OUT OF RANGE" % v ]

	f.close()
	return results

def check_itrim(conn, sockets, fname):
	print "CHECK REF CURRENT TRIM"
	
	results = {}
	f = open(fname, "w")
	conn.initializeSystem()
	asicsConfig = conn.getAsicsConfig()
	for m,a,t in sockets:
		ac = asicsConfig[(0, 0, 2*m+a)]
		v = ac.globalConfig.getValue("Iref_cal_DAC")
		f.write("%d\t%d\t%d\n" % (m, a, v))
		
	f.close()
	return results

def bga_check_id(conn, sockets):
	print "CHECK ASIC ID SETTING"
	results = {}
	
	## Test other communication features
	## effect of chip ID
	gc = conn._Connection__asic_module.AsicGlobalConfig()
	for m,a,t in sockets:
		for board_id in [  0b1000, 0b100, 0b10, 0b1, 0b0]:
			try:
				t.set_uut_board_id(board_id)
				busID = m
				chipID = 2*board_id + a
				readID = 2*m + a
				conn._Connection__tofhir2_cmd(0, 0, busID, chipID, readID, 32, False, True, gc)

			except tofhir2.ConfigurationError as e:
				results[m,a] = [ "CHIP_ID FAIL" ]
				
	return results


def check_rx_phase(conn, sockets, ddir, acquire=True, fe_mode=False):
	print "CHECK RX PHASE SELECTION"

	# This test fails on read_csv if there are no active sockets
	if sockets == []: return {}

	if acquire:
		asicsConfig0 = conn.getAsicsConfig()	

		
		# Determine firmware mode and build global TX config
		system_mode = conn.read_config_register(0, 0, 16, 0x0104)
		tdc_clk_div, ddr, tx_nlinks = conn._Connection__getAsicLinkConfiguration(0,0)
		gctx = conn._Connection__asic_module.AsicGlobalConfigTX()
		c_tx_mode = 0b0000

		# Select DDR mode
		if ddr:
			c_tx_mode |= 0b1000
		else:
			c_tx_mode |= 0b0000

		# Select primary/secondary TX
		if system_mode & 0x300 == 0x000:
			c_tx_mode |= 0b0000
		elif system_mode & 0x300 == 0x100:
			c_tx_mode |= 0b0100

		gctx.setValue("c_tx_mode", c_tx_mode)

		# Select dual TX (for TOFHiR 2B onwards only)
		if (system_mode & 0xF >= 0x3) and (system_mode & 0x300 == 0x200):
			gctx.setValue("c_dual", 1)

		gctx.setValue("c_tx_clps", 1023)
		
		
		gc = conn._Connection__asic_module.AsicGlobalConfig()
		gc.setValue("c_ext_tp_en", 1)
		cc = conn._Connection__asic_module.AsicChannelConfig()
		cc.setValue("c_tgr_main", 0b01)


		phase_range = 56*6

		cmd_fail_count = pd.DataFrame(0, index=np.arange(0, len(sockets)*phase_range), columns=["phase", "m", "a", "count" ])

		gc = conn._Connection__asic_module.AsicGlobalConfig()

		index = 0
		for p in range(phase_range):
			conn.spi_master_execute(0, 0, 0x02, 3,
				64,
				1, 63,
				3, 4,
				0, 15,
				0, 15,
				[0x00, 0x00]
			);

			phase = float(p)/phase_range
			conn.set_test_pulse_febds(3, 1024, 0.5, False)
			
			
			chip_communication_failure = dict([ ((m,a),0) for m,a,t in sockets ])

			
			# Reset the ASICs configuration
			conn.write_config_register(0, 0, 2, 0x0201, 0b00)
			for k in range(10):
				# Generate multiple resets to train the RESYNC receiver
				conn.write_config_register(0, 0, 1, 0x300, 0b1)
				conn.write_config_register(0, 0, 1, 0x300, 0b0)
				
			time.sleep(0.001)

			for m,a,t in sockets:
				try:
					conn._Connection__tofhir2_cmd(0, 0, m, a, 2*m+a, 33, True, False, gctx)
					conn._Connection__tofhir2_cmd(0, 0, m, a, 2*m+a, 33, True, False, gctx)
					
					# And now re-upload the configuration
					conn._Connection__doAsicCommand(0, 0, 2*m+a, "wrGlobalCfg", value=gc)
					for channelID in [15]:
						conn._Connection__doAsicCommand(0, 0, 2*m+a, "wrChCfg", value=cc, channel=channelID)
								
			
					
				except tofhir2.ConfigurationError:
					chip_communication_failure[m,a] = 1
					
					
			for m,a,t in sockets:
				c = chip_communication_failure[m,a]
				cmd_fail_count.iloc[index] = [phase, m, a, c]
				index += 1
							

		cmd_fail_count.to_csv("%s/rx_phase_cmd_fail.tsv" % (ddir,), sep="\t", encoding="utf-8-sig")
	
		conn.setTestPulseNone()
		conn.setAsicsConfig(asicsConfig0)

	# RX phase scan for fe boards needs ranges to be rechecked
	if fe_mode:
		return {}
	
	def delta(x):
		return np.max(x) - np.min(x)
	

	SPLIT = 0.8
	cmd_fail_count = pd.read_csv("%s/rx_phase_cmd_fail.tsv" % (ddir,), sep="\t", encoding="utf-8-sig")
	results = {}


	# Analsysis step 1: accept up to a single failing phase in the 0.8 .. 1.0 range
	# a failure here is treated as a 
	cmd_failed = cmd_fail_count.loc[(cmd_fail_count["count"] > 0) & (cmd_fail_count["phase"] > SPLIT)]
	cmd_failed = cmd_failed.groupby(["m", "a"])["phase"].agg(["min", "max", delta ]).reset_index()
	cmd_failed = cmd_failed.set_index(['m','a']).T.to_dict()
	for (m,a) in cmd_failed.keys():
		v = cmd_failed[(m,a)]['delta']
		if v > 0:
			results[ int(m), int(a)] = [ "RX PHASE FAIL DELTA2 %5.3f > 0.0" % v ]


	# Analsysis step 2: apply normal criteria in the 0 .. 0.8 clock cycle range
	cmd_failed = cmd_fail_count.loc[(cmd_fail_count["count"] > 0) & (cmd_fail_count["phase"] <= SPLIT)]
	cmd_failed = cmd_failed.groupby(["m", "a"])["phase"].agg(["min", "max", delta ]).reset_index()
	cmd_failed = cmd_failed.set_index(['m','a']).T.to_dict()
	for (m,a) in cmd_failed.keys():
		v = cmd_failed[(m,a)]['min']
		if v < 0.075:
			results[ int(m), int(a)] = [ "RX PHASE FAIL MIN %5.3f < 0.075" % v]

		v = cmd_failed[(m,a)]['max']
		if v > 0.230:
			results[ int(m), int(a)] = [ "RX PHASE FAIL MAX %5.3f > 0.230" % v ]

		v = cmd_failed[(m,a)]['delta']
		if v > 0.051:
			results[ int(m), int(a)] = [ "RX PHASE FAIL RANGE %5.3f > 0.051" % v]



	return results
	
def check_multiple_links(conn, sockets):
	print "CHECK MULTIPLE TX LINK MODES"
	results = {}
	
	for mode in [ 0x200, 0x100, 0x000 ]:
		current_mode = conn.read_config_register(0, 0, 16, 0x0104)
		current_mode &= ~0x300
		current_mode |= mode
		
		conn.write_config_register(0, 0, 16, 0x0104, current_mode)
		
		conn.initializeSystem()
		asicsConfig0 = conn.getAsicsConfig()
		asicsConfig = deepcopy(asicsConfig0)
		for ac in asicsConfig.values():
			ac.globalConfig.setValue("c_ext_tp_en", 1)
			ac.channelConfig[15].setValue("c_tgr_main", 0b01)
		conn.setAsicsConfig(asicsConfig)
		
		conn.set_test_pulse_febds(3, 1024, 0.5, False)
		
		events = conn.acquireAsPandas(6.25E-9 * 1024 * 2048)
		event_counts = events.groupby("channelID")["t1Coarse"].agg(["min", "max", "count"]).reset_index()
				
		for m,a,t in sockets:
			channelID = (2*m + a) * 32  + 15
			try:
				if event_counts.loc[event_counts["channelID"] == channelID]["count"].min() < 2000:
					results[m,a] = [ "MULTILINK MODE 0x%04X CHECK FAIL EVT" % mode ]
			except KeyError:
				results[m,a] = [ "MULTILINK MODE 0x%04X CHECK FAIL EVT" % mode ]
			
			
			if (0,0,2*m+a) not in asicsConfig.keys():
				results[m,a] = [ "MULTILINK MODE 0x%04X CHECK FAIL CMD" % mode ]


	conn.setTestPulseNone()
	conn.setAsicsConfig(asicsConfig0)
	return results

def check_discriminators(conn, sockets, disc_range, mode, ddir, acquire=True):
	print "CHECK DISCRIMINATORS"
	if mode == "fast":
		step = 3
	else:
		step = 1
	
	if acquire:
		os.system("./acquire_threshold_calibration --no-bias --config /dev/null --lsb %(disc_range)d --step %(step)d -o %(ddir)s/disc_calibration%(disc_range)d" % locals())
		
	os.system("./process_threshold_calibration --step %(step)d --config %(ddir)s/config.ini -i %(ddir)s/disc_calibration%(disc_range)d -o %(ddir)s/disc_calibration%(disc_range)d.tsv" % locals())
	
	df = pd.read_csv("%(ddir)s/disc_calibration%(disc_range)d.tsv" % locals(), sep="\t", header=None, comment="#",
		names=["port_id", "slave_id", "asic_id", "channel_id", 	"baseline_T", "baseline_E", "zero_T1", "zero_T2", "zero_E", "noise_T1", "noise_T2", "noise_E"]
	)
	
        noisecriteria = {
		0:[2, 1, 0.6],
                1:[1,0.5,0.3],
                2:[0.67,0.33,0.3],
                3:[0.5, 0.25, 0.3]
        }
        zerocriteria = {
		0:[100, 50, 16],
                1:[50,25,8],
                2:[33,17,5],
                3:[25, 13, 4]
        }
	results = {}
	for m,a,t in sockets:
		results[m,a] = []
		for ch in range(32):
			asic_id = 2*m + a
			
			df2 = df[(df["asic_id"] == asic_id) & (df["channel_id"] == ch)]
			
			try:
				v = df2["noise_T1"].iloc[0]					
				if v > noisecriteria[disc_range][0]:
					results[m,a].append("DISC CH %d NOISE T1 %4.1f > %4.1f" % (ch, v, noisecriteria[disc_range][0]))
					continue
				v = df2["noise_T2"].iloc[0]					
				if v > noisecriteria[disc_range][1]:
					results[m,a].append("DISC CH %d NOISE T2 %4.1f > %4.1f" % (ch, v, noisecriteria[disc_range][1]))
					continue
				v = df2["noise_E"].iloc[0]					
				if v > noisecriteria[disc_range][2]:
					results[m,a].append("DISC CH %d NOISE E %4.1f > %4.1f" % (ch, v, noisecriteria[disc_range][2]))
					continue
				
				v = df2["zero_T1"].iloc[0]					
				if v <= 0:
					results[m,a].append("DISC CH %d BASELINE T1 <= 0" % ch)
					continue
				
				if v > zerocriteria[disc_range][0]:
					results[m,a].append("DISC CH %d BASELINE T1 %4.1f > %4.1f" % (ch, v, zerocriteria[disc_range][0]))
					continue
				
				v = df2["zero_T2"].iloc[0]					
				if v <= 0:
					results[m,a].append("DISC CH %d BASELINE T2 <= 0" % ch)
					continue
				
				if v > zerocriteria[disc_range][1]:
					results[m,a].append("DISC CH %d BASELINE T2 %4.1f > %4.1f" % (ch, v, zerocriteria[disc_range][1]))
					continue
				
				v = df2["zero_E"].iloc[0]
				# This requirement was discarded
				#if v <= 0:
					#results[m,a].append("DISC CH %d BASELINE E <= 0" % ch)
					#continue
				
				if v > zerocriteria[disc_range][2]:
					results[m,a].append("DISC CH %d BASELINE E %4.1f > %4.1f" % (ch, v, zerocriteria[disc_range][2]))
					continue
				
				
			except IndexError as e:
				results[m,a].append("DISC CH %d MISSING" % ch)
				continue
	
	return results

def check_tdc(conn, sockets, mode, ddir, acquire=True):
	print "CHECK TDC"
	# WARNING:
	# "mode" is not yet implemented, all acquisitions are done in full
	
	if acquire:
		os.system("./acquire_tdc_calibration --config /dev/null -o %(ddir)s/tdc_calibration" % locals())
	
	tmp_dir = tempfile.mkdtemp(suffix="tofhir_bga")
	os.system("./process_tdc_calibration --config %(ddir)s/config.ini -i %(ddir)s/tdc_calibration -o %(ddir)s/tdc_calibration --tmp-prefix %(tmp_dir)s" % locals())	

	df = pd.read_csv("%(ddir)s/tdc_calibration.tsv" % locals(), sep="\t", header=None, comment="#",
		names=["port_id", "slave_id", "asic_id", "channel_id", 	"tac_id", "branch_id", "t0", "a0", "a1", "a2", "sigma" ]
		)
	
	results = {}
	for m,a,t in sockets:
		results[m,a] = []
		for ch in range(32):
			for tac_id in range(8):
				for branch_id in [1,2]:
			
					asic_id = 2*m + a
					
					df2 = df[(df["asic_id"] == asic_id) & (df["channel_id"] == ch) & (df["tac_id"] == tac_id) & (df["branch_id"] == branch_id)]
					
					try:
						v = df2["sigma"].iloc[0]					
						if v > 62.5/6250:
							results[m,a].append("TDC CH %d RMS %4.1f > 62.5ps" % (ch, v*6250))
							continue
						
						a1 = df2["a1"].iloc[0]					
						if a1 < 440:
							results[m,a].append("TDC CH %d SLOPE %4.1f  < 440" % (ch, a1))
							continue
							
						a0 = df2["a0"].iloc[0]
                                                maxdac = 1.5 * a1 + a0
						if maxdac > 1000:
							results[m,a].append("TDC CH %d MAX DAC %5.0f > 1000" % (ch, maxdac))
							continue
						
						a2 = df2["a2"].iloc[0]
                                                # deltabin = 1.5 * a1 + a0
						# if maxdac > 1000:
						# 	results[m,a].append("TDC CH %d MAX DAC %5.0f > 1000" % (ch, maxdac))
						# 	continue
						
					except IndexError as e:
						results[m,a].append("TDC CH %d TAC %d BRANCH %d MISSING" % (ch, tac_id, branch_id))
						continue

	os.system("rm -rf %(tmp_dir)s" % locals())
	return results

def check_qdc(conn, sockets, att, mode, ddir, acquire=True):
	print "CHECK QDC"
	# WARNING
	# "mode" is not implemented, all acquisitions are done in full
	
	if acquire:
		os.system("./acquire_qdc_calibration --config /dev/null -o %(ddir)s/qdc_calibration --att %(att)d" % locals())
	
	tmp_dir = tempfile.mkdtemp(suffix="tofhir_bga")
	os.system("./process_qdc_calibration --config %(ddir)s/config.ini -i %(ddir)s/qdc_calibration%(att)d -o %(ddir)s/qdc_calibration%(att)d --tmp-prefix %(tmp_dir)s" % locals())	

	df = pd.read_csv("%(ddir)s/qdc_calibration%(att)d.tsv" % locals(), sep="\t", header=None, comment="#",
		names=["port_id", "slave_id", "asic_id", "channel_id", 	"tac_id", "trim", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "xx", "sigma" ]
		)

	results = {}
	for m,a,t in sockets:
		results[m,a] = []
		for ch in range(32):
			for tac_id in range(8):
				asic_id = 2*m + a
				
				df2 = df[(df["asic_id"] == asic_id) & (df["channel_id"] == ch) & (df["tac_id"] == tac_id)]
				
				try:		
					# v = df2["sigma"].iloc[0]					
					# if v > 10.0:
					# 	results[m,a].append("QDC CH %d RMS %4.1f  > 10.0" % (ch, v))
					# 	continue

					p0 = df2["p0"].iloc[0]
					p1 = df2["p1"].iloc[0]

					if p0 > 100.0:
						results[m,a].append("QDC CH %d HIGH PEDESTAL P0 %4.0f  > 100.0" % (ch, p0))
						continue
					if p1 < -2.0 or p1 > 15:
						results[m,a].append("QDC CH %d PEDESTAL P1 %4.0f OUT OF RANGE" % (ch, p1))
						continue
					
					# pass
				
					
				except IndexError as e:
					results[m,a].append("QDC CH %d TAC %d MISSING" % (ch, tac_id))
					continue

	os.system("rm -rf %(tmp_dir)s" % locals())
	return results


def setup_xxtp(conn, sockets, att, disc_range, ddir, fetp):

	conn.initializeSystem()
	conn.setTestPulsePLL(500, 10240, 0.0)
	
	asicsConfig = conn.getAsicsConfig()
	
	qdcTrim = config.readQDCTrimTable("%(ddir)s/qdc_calibration%(att)d.tsv" % locals())
	# Fill qdcTrim table with a default value for missing channels
	for ((p,s,a),ch) in itertools.product(asicsConfig.keys(), [x for x in range(32) ]):
		if not qdcTrim.has_key((p,s,a,ch)):
			qdcTrim[p,s,a,ch] = 24	
	
	for (p,s,a), ac in asicsConfig.items():

		gc = ac.globalConfig
		if fetp:
				gc.setValue("c_ext_tp_en", 1)
				gc.setValue("c_fetp_en", 1)
		
		for ch, cc in enumerate(ac.channelConfig):
				cc.setValue("cfg_a3_range_t1", disc_range)
				cc.setValue("cfg_a3_range_t2", 3)
				cc.setValue("cfg_a3_range_e", 3)
				cc.setValue("cfg_a3_ith_t1", 63)
				cc.setValue("cfg_a3_ith_t2", 63)
				cc.setValue("cfg_a3_ith_e", 63)
				cc.setValue("c_tgr_main", 0b11)
				cc.setValue("c_tgr_t1", 0)
				cc.setValue("c_tgr_q", 0)
				cc.setValue("c_tgr_t2", 0)
				cc.setValue("c_tgr_q", 0)
				cc.setValue("c_tgr_v", 0)
				cc.setValue("cfg_a2_dcr_delay_t", 0b11111111)
				cc.setValue("cfg_a2_dcr_delay_e", 0b0111111)
				cc.setValue("c_min_q", 2)
				cc.setValue("c_max_q", 2)
				cc.setValue("cfg_a2_attenuator_gain", att)
				cc.setValue("cfg_a2_dc_trim", qdcTrim[p,s,a,ch])
				
	conn.setAsicsConfig(asicsConfig)
	
	_, disc_calibration = config.readDiscCalibrationsTable("%(ddir)s/disc_calibration%(disc_range)d.tsv" % locals())
	disc_calibration = dict([ ((a, ch), zero_t1) for (p, s, a, ch), (zero_t1, zero_t2, zero_e) in disc_calibration.items() ])
	
	# Fill disc calibration table with a default value for missing channels
	for ((p,s,a),ch) in itertools.product(asicsConfig.keys(), [x for x in range(32) ]):
		if not disc_calibration.has_key((p,s,a,ch)):
			disc_calibration[p,s,a,ch] = 56.0

	return disc_calibration




def check_fetp_tres(conn, sockets, att, ddir, acquire=True):

	fName = "%s/fetp_tres_scan" % ddir
	if acquire:
			print "TESTING: FETP TRES"
			disc_calibration = setup_xxtp(conn, sockets, att, 1, ddir, True)
		
			asicsConfig0 = conn.getAsicsConfig()
			
			conn.openRawAcquisition(fName)

			for ch in range(32):
				for m,a,t in sockets:
					t.injector_enable(ch, None, load_only=True)
				

				for ith in range(10, 64):
					asicsConfig = deepcopy(asicsConfig0)
					ith_in_range = False
					
					for (p,s,a), ac in asicsConfig.items():
						gc = ac.globalConfig
						gc.setValue("Pulse_Amplitude", 31)
				
						cc = ac.channelConfig[ch]
						
						new_ith = int(disc_calibration[a,ch] + ith)
						if new_ith < 64:
							cc.setValue("cfg_a3_ith_t1", new_ith)
							cc.setValue("cfg_a1_fetp_en", 1)
							cc.setValue("c_tgr_main", 0b00)
							ith_in_range = True
						
							
					if not ith_in_range:
						# There is no ASIC for which ith is <= 63
						# So we don't need to scan any further
						break
					
					print "FETP TRMS ", ch, ith
					conn.setAsicsConfig(asicsConfig)
					conn.acquire(0.1, ch, ith)
						
			conn.closeAcquisition()
			
			# Disable stuf and return to normal
			conn.setAsicsConfig(asicsConfig0)
			for m, a, t in sockets:
				t.injector_disable()
	
	os.system("./convert_raw_to_singles --config %(ddir)s/config.ini -i %(fName)s -o %(fName)s --writeBinary --att %(att)d" % locals())
	os.system("""root -b -l -q plot_fetp_calibration.cc+\\(\\"%(fName)s\\",10\\)""" % locals())
	
	df = pd.read_csv("%(fName)s.tsv" % locals(), sep="\t", header=None, names=["asic_id", "channel_id", "amplitude", "trms", "emean", "erms"])
	
	results = {}
	for m,a,t in sockets:
		results[m,a] = []
		for ch in range(32):
			asic_id = 2*m + a
			
			df2 = df[(df["asic_id"] == asic_id) & (df["channel_id"] == ch)]
			
			try:
				trms = df2["trms"].iloc[0]
				
				if trms == 0:
					results[m,a].append("FETP CH %d LOW COUNTS" % ch)
					continue
					
				if trms > 40:
					results[m,a].append("FETP CH %d TRMS %4.1f > 40 ps" % (ch, trms))
					continue

				
				
			except IndexError as e:
				results[m,a].append("FETP CH %d MISSING" % ch)
				continue
				
	return results

def check_fetp_eres(conn, sockets, att, ddir, acquire=True):

	fName = "%s/fetp_eres_scan" % ddir
	if acquire:
			print "TESTING: FETP ERES"
			disc_calibration = setup_xxtp(conn, sockets, att, 2, ddir, True)
		
			asicsConfig0 = conn.getAsicsConfig()
			
			conn.openRawAcquisition(fName)

			for ch in range(32):
				for m,a,t in sockets:
					t.injector_enable(ch, None, load_only=True)
				
				for amp in range(1,32,4):
					asicsConfig = deepcopy(asicsConfig0)
					
					for (p,s,a), ac in asicsConfig.items():
						gc = ac.globalConfig
						gc.setValue("Pulse_Amplitude", amp)
				
						cc = ac.channelConfig[ch]
						cc.setValue("cfg_a3_ith_t1", disc_calibration[a,ch] + 10)
						cc.setValue("cfg_a1_fetp_en", 1)
						cc.setValue("c_tgr_main", 0b00)

					print "FETP ERMS ", ch, amp
					conn.setAsicsConfig(asicsConfig)
					conn.acquire(0.1, ch, amp)
						
			conn.closeAcquisition()
			
			# Disable stuf and return to normal
			conn.setAsicsConfig(asicsConfig0)
			for m, a, t in sockets:
				t.injector_disable()
	
	os.system("./convert_raw_to_singles --config %(ddir)s/config.ini -i %(fName)s -o %(fName)s --writeBinary --att %(att)d" % locals())
	os.system("""root -b -l -q plot_fetp_energy.cc+\\(\\"%(fName)s\\"\\)""" % locals())
	
	df = pd.read_csv("%(fName)s.tsv" % locals(), sep="\t", header=None, names=["asic_id", "channel_id", "b", "m"])
	
	results = {}
	for m,a,t in sockets:
		results[m,a] = []
		for ch in range(32):
			asic_id = 2*m + a
			
			df2 = df[(df["asic_id"] == asic_id) & (df["channel_id"] == ch)]
			
			try:
				eslope = df2["m"].iloc[0]
				
				if eslope < 3 or eslope > 13:
					results[m,a].append("FETP CH %d ENERGY SLOPE %.2f NOT IN [3,13] RANGE" % (ch,eslope))
					continue

				
				
			except IndexError as e:
				results[m,a].append("FETP CH %d MISSING ENERGY CAL" % ch)
				continue
				
	return results


def check_extp_tres(conn, sockets, att, ddir, acquire=True):

	fName = "%s/extp_tres_scan" % ddir
	if acquire:
			print "TESTING: EXTP TRES"
			disc_calibration = setup_xxtp(conn, sockets, att, 1, ddir, False)
		
			asicsConfig0 = conn.getAsicsConfig()
			
			conn.openRawAcquisition(fName)

			for ch in range(32):
				for m,a,t in sockets:
					t.injector_enable(ch, 0xFFFF)
				

				for ith in range(10, 64):
					asicsConfig = deepcopy(asicsConfig0)
					ith_in_range = False
					
					for (p,s,a), ac in asicsConfig.items():
						cc = ac.channelConfig[ch]
						
						new_ith = int(disc_calibration[a,ch] + ith)
						if new_ith < 64:
							cc.setValue("cfg_a3_ith_t1", new_ith)
							cc.setValue("c_tgr_main", 0b00)
							ith_in_range = True
						
							
					if not ith_in_range:
						# There is no ASIC for which ith is <= 63
						# So we don't need to scan any further
						break
					
					print "EXTP TRMS ", ch, ith
					conn.setAsicsConfig(asicsConfig)
					conn.acquire(0.1, ch, ith)
						
			conn.closeAcquisition()
			
			# Disable stuf and return to normal
			conn.setAsicsConfig(asicsConfig0)
			for m, a, t in sockets:
				t.injector_disable()
	
	os.system("./convert_raw_to_singles --config %(ddir)s/config.ini -i %(fName)s -o %(fName)s --writeBinary --att %(att)d" % locals())
	os.system("""root -b -l -q plot_fetp_calibration.cc+\\(\\"%(fName)s\\",15\\)""" % locals())
	
	df = pd.read_csv("%(fName)s.tsv" % locals(), sep="\t", header=None, names=["asic_id", "channel_id", "amplitude", "trms", "emean", "erms"])
	
	results = {}
	for m,a,t in sockets:
		results[m,a] = []
		for ch in range(32):
			asic_id = 2*m + a
			
			df2 = df[(df["asic_id"] == asic_id) & (df["channel_id"] == ch)]
			
			try:
				trms = df2["trms"].iloc[0]
				
				if trms == 0:
					results[m,a].append("EXTP CH %d LOW COUNTS" % ch)
					continue
					
				if trms > 50:
					results[m,a].append("EXTP CH %d TRMS %4.1f > 50 ps" % (ch, trms))
					continue
				
			except IndexError as e:
				results[m,a].append("EXTP CH %d MISSING" % ch)
				continue
				
	return results

def check_extp_eres(conn, sockets, att, ddir, acquire=True):

	fName = "%s/extp_eres_scan" % ddir
	if acquire:
			print "TESTING: EXTP ERES"
			disc_calibration = setup_xxtp(conn, sockets, att, 2, ddir, False)
		
			asicsConfig0 = conn.getAsicsConfig()
			
			conn.openRawAcquisition(fName)

			for ch in range(32):
				for amp in range(1,32,4):
					for m,a,t in sockets:
						t.injector_enable(ch, 0x8000 + amp * 0x8000/32)

					
					asicsConfig = deepcopy(asicsConfig0)
					
					for (p,s,a), ac in asicsConfig.items():
						cc = ac.channelConfig[ch]
						cc.setValue("cfg_a3_ith_t1", disc_calibration[a,ch] + 10)
						cc.setValue("c_tgr_main", 0b00)

					print "EXTP ERMS ", ch, amp
					conn.setAsicsConfig(asicsConfig)
					conn.acquire(0.1, ch, amp)
						
			conn.closeAcquisition()
			
			# Disable stuf and return to normal
			conn.setAsicsConfig(asicsConfig0)
			for m, a, t in sockets:
				t.injector_disable()
	
	os.system("./convert_raw_to_singles --config %(ddir)s/config.ini -i %(fName)s -o %(fName)s --writeBinary --att %(att)d" % locals())
	os.system("""root -b -l -q plot_fetp_energy.cc+\\(\\"%(fName)s\\"\\)""" % locals())
	
	df = pd.read_csv("%(fName)s.tsv" % locals(), sep="\t", header=None, names=["asic_id", "channel_id", "b", "m"])
	
	results = {}
	for m,a,t in sockets:
		results[m,a] = []
		for ch in range(32):
			asic_id = 2*m + a
			
			df2 = df[(df["asic_id"] == asic_id) & (df["channel_id"] == ch)]
			
			try:
				eslope = df2["m"].iloc[0]
				
				if eslope < 5 or eslope > 35:
					results[m,a].append("EXTP CH %d ENERGY SLOPE %.2f NOT IN [5,35] RANGE" % (ch,eslope))
					continue

				
				
			except IndexError as e:
				results[m,a].append("EXTP CH %d MISSING ENERGY CAL" % ch)
				continue
				
	return results

def value_in(v, limits):
	l, u = limits
	return (v >= l) and (v <= u)

def check_aldo(conn, sockets, step, gain, ddir, acquire=True, fe_mode=False):
	results = {}
	for m,a,t in sockets:
		results[m,a] = []

	if acquire:
		print "TESTING: ALDO"
		asicsConfig0 = conn.getAsicsConfig()
		
		f = open("%s/aldo.tsv" % ddir, "w")
		
		for aldo_range in [0, 1]:
			for aldo_dac in [ x for x in range(0, 255, step)] + [ 255]:
				sys.stdout.write(".")
				sys.stdout.flush()
				
				asicsConfig = deepcopy(asicsConfig0)
				for ac in asicsConfig.values():
					gc = ac.globalConfig
					if aldo_range == 0:
						gc.setValue("Valdo_A_Gain", 0)
						gc.setValue("Valdo_B_Gain", 0)
						gc.setValue("c_aldo_range", 0b00)
					else:
						gc.setValue("Valdo_A_Gain", 1)
						gc.setValue("Valdo_B_Gain", 1)
						gc.setValue("c_aldo_range", 0b11)

					gc.setValue("c_aldo_en", 0b11)
					gc.setValue("Valdo_A_DAC", aldo_dac)
					gc.setValue("Valdo_B_DAC", aldo_dac)
					
					
				conn.setAsicsConfig(asicsConfig)
				
				# ALDO HV seems to need some time to stabilize
				if fe_mode and aldo_dac == 0:
					time.sleep(0.1)
				
				for m, a, t in sockets:
					for aldo_id in [0, 1]:
						v = t.get_bias_voltage(a, aldo_id)
						i = t.get_bias_current(a, aldo_id) if fe_mode else 0.0
						f.write("%d\t%d\t%d\t%d\t%d\t%f\t%e\n" % (m, a, aldo_id, aldo_range, aldo_dac, v, i))
			
		
		sys.stdout.write("\n")
		f.close()
		conn.setAsicsConfig(asicsConfig0)
		
	df = pd.read_csv("%(ddir)s/aldo.tsv" % locals(), sep="\t", header=None, 
			names=["module_id", "asic_id", "aldo_id", 
				"aldo_range", "aldo_dac", "vout", "iout" ])

	for m,a,t in sockets:
		for aldo_id in range(2):
			for aldo_range in range(2):
				df2 = df[(df["module_id"] == m) & (df["asic_id"] == a) & (df["aldo_id"] == aldo_id) & (df["aldo_range"] == aldo_range)]
				
				# Exlude top 20% of range
				df2 = df2[df2["aldo_dac"] < 250]
				
				aldo_dac = df2["aldo_dac"]
				vout = df2["vout"]
				
				lower = min(vout)
				upper = max(vout)
				slope, b = np.polyfit(aldo_dac, vout, 1)
				
				error = vout - (slope * aldo_dac + b)
				max_inl = max(abs(error)) / slope 


				if fe_mode == False:
					if aldo_range == 0:
						slope_limits = (0.000445, 0.000485)
						b_limits = (0.78, 0.86)
						inl_limits = (0, 5)
					else:
						slope_limits = (0.00089, 0.00096)
						b_limits = (0.71, 0.77)
						inl_limits = (0, 8)
				else:
					# Wide values to avoid failures
					if aldo_range == 0:
						slope_limits = (0.020, 0.022)
						b_limits = (30, 40)
						inl_limits = (0, 15)
					else:
						slope_limits = (0.040, 0.042)
						b_limits = (30, 40)
						inl_limits = (0, 15)

				if not value_in(slope, slope_limits):
					results[m,a].append("ALDO %(aldo_id)d RANGE %(aldo_range)d SLOPE %(slope)5.6f OUT OF BOUNDS" % locals())
					continue

				if not value_in(b, b_limits):
					results[m,a].append("ALDO %(aldo_id)d RANGE %(aldo_range)d INTERCEPT %(b)5.6f OUT OF BOUNDS" % locals())
					continue

				if not value_in(max_inl, inl_limits):
					results[m,a].append("ALDO %(aldo_id)d RANGE %(aldo_range)d MAX INL %(max_inl)4.1f TOO LARGE" % locals())
					continue
				
					
	return results


def check_pt1000(conn, testers, ddir, acquire=True):

	results = {}
	if acquire:
		print "CHECK PT1000 PATH"
		f = open("%(ddir)s/pt1000.tsv" % locals(), "w")
		for m, t in testers:
			r_list = t.get_pt1000_resistance()
			for path in [0, 1]:
				f.write("%d\t%d\t%f\n" % (m, path, r_list[path]))

		f.close()

	df = pd.read_csv("%(ddir)s/pt1000.tsv" % locals(), sep="\t", header=None,
			names=["module_id", "path_id", "r"])

	df = df.set_index(["module_id", "path_id"]).T.to_dict()

	for m, t in testers:
		results[m] = []
		for path in [0, 1]:
			r = df[m, path]["r"]
			if r > 10:
				results[m].append("PT1000 PATH %d HAS HIGH RESISTANCE %f" % (path, r))


	return results

def check_tec(conn, testers, ddir, acquire=True):
	results = {}
	if acquire:
		print "CHECK TEC PATH"
		f = open("%(ddir)s/tec.tsv" %locals(), "w")
		conn.set_tec_power(True)
		time.sleep(0.1)
		for m, t in testers:
			r = t.get_tec_resistance()
			f.write("%d\t%f\n" % (m, r))
		
		f.close()
		conn.set_tec_power(False)

	df = pd.read_csv("%(ddir)s/tec.tsv" % locals(), sep="\t", header=None,
			names=["module_id", "r"])

	df = df.set_index(["module_id"]).T.to_dict()

	for m, t in testers:
		results[m] = []
		r = df[m]["r"]
		if r > 10:
			results[m].append("TAC PATH HAS HIGH RESISTANCE %f" % r)
	return results

def check_aldo_fe(conn, testers, ddir, acquire=True):
	results = {}
	
	if acquire:
		df = pd.read_csv("%(ddir)s/aldo.tsv" % locals(), sep="\t", header=None,
				names=["module_id", "asic_id", "aldo_id",
					"aldo_range", "aldo_dac", "vout", "iout" ])

		df = df[df["aldo_range"] == 1]
		df = df.set_index(["module_id", "asic_id", "aldo_id", "aldo_dac"]).T.to_dict()

		f = open("%(ddir)s/aldo_fe.tsv" % locals(), "w")

		asicsConfig0 = conn.getAsicsConfig()
		for aldo_dac in range(0, 1, 7):
			asicsConfig = deepcopy(asicsConfig0)
			for ac in asicsConfig.values():
				gc = ac.globalConfig
				gc.setValue("Valdo_A_Gain", 1)
				gc.setValue("Valdo_B_Gain", 1)
				gc.setValue("c_aldo_range", 0b11)

				gc.setValue("c_aldo_en", 0b11)
				gc.setValue("Valdo_A_DAC", aldo_dac)
				gc.setValue("Valdo_B_DAC", aldo_dac)


			conn.setAsicsConfig(asicsConfig)

			# ALDO HV seems to need some time to stabilize
			if aldo_dac == 0:
				time.sleep(1)

			for m, t in testers:
				for asic_id in [0, 1]:
					for aldo_id in [0, 1]:
						v_loaded = df[m, asic_id, aldo_id, aldo_dac]["vout"]
						i_loaded = df[m, asic_id, aldo_id, aldo_dac]["iout"]
						v_unloaded = t.get_bias_voltage(asic_id, aldo_id)
						i_unloaded = t.get_bias_current(asic_id, aldo_id)
						f.write("%d\t%d\t%d\t%d\t%f\t%f\t%e\t%e\n" % (m, asic_id, aldo_id, aldo_dac, v_loaded, v_unloaded, i_loaded, i_unloaded))
						status = t.check_bias_voltage(asic_id, aldo_id, v_unloaded)
						if status != []:
							results[m] = "BIAS PRESENCE CHECK FAILED FOR ASIC %d ALDO %d" % (a, aldo)

		conn.setAsicsConfig(asicsConfig0)
		f.close()


	df = pd.read_csv("%(ddir)s/aldo_fe.tsv" % locals(), sep="\t", header=None,
				names=["module_id", "asic_id", "aldo_id",
					"aldo_dac", "v_loaded", "v_unloaded", "i_loaded", "i_unloaded" ])

	return results
