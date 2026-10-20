# -*- coding: utf-8 -*-
# Run from the build directory with daqd running. Works with python2 and python3.
from __future__ import print_function
# Probes ASIC 0 (port 0, slave 0, bus 0): reads, writes default global config, reads back, reads status
import sys, os
sys.path.insert(0, os.getcwd())
from petsys import daqd, tofhir2b
c = daqd.Connection()
c.getActiveFEBDs()
c._Connection__asic_module = tofhir2b
cmd = c._Connection__tofhir2_cmd_ll
gc = tofhir2b.AsicGlobalConfig()
for attempt in range(3):
	for name, reg, write, val in [("rdGlobalCfg", 32, False, tofhir2b.AsicGlobalConfig()), ("wrGlobalCfg", 32, True, gc), ("rdGlobalCfg", 32, False, tofhir2b.AsicGlobalConfig()), ("rdStatus", 34, False, tofhir2b.AsicGlobalConfigStatus())]:
		try:
			st, rep = cmd(0, 0, 0, 0, 0, reg, write, True, val)
			extra = ""
			if name == "rdGlobalCfg":
				extra = "matches default: %s  diff bits: %d" % (rep == gc, (rep ^ gc).count())
			print(attempt, name, "status 0x%02x" % st, "len", len(rep), extra)
		except Exception as e:
			print(attempt, name, "EXC", type(e).__name__, e)
