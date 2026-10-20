# -*- coding: utf-8 -*-
# Run from the build directory with daqd running. Works with python2 and python3.
from __future__ import print_function
# Read-only FEB/D diagnostics (reads registers only)
import sys, os
sys.path.insert(0, os.getcwd())
from petsys import daqd
c = daqd.Connection()
print("active ports:", c.getActivePorts())
print("active FEB/Ds:", c.getActiveFEBDs(), "trigger unit:", c.getTriggerUnit())
for p, s in c.getActiveFEBDs():
	r = lambda w, a: c.read_config_register(p, s, w, a)
	print("FEB/D (%d,%d)" % (p, s))
	print("  system mode   0x0104 = 0x%04X" % r(16, 0x0104))
	print("  asic type     0x0102 = 0x%04X" % r(16, 0x0102))
	print("  febd type     0x0022 = 0x%04X" % r(16, 0x0022))
	print("  fem type      0x0002 = 0x%04X" % r(16, 0x0002))
	print("  bias type     0x0012 = 0x%04X" % r(16, 0x0012))
	print("  n links-1     0x0100 = %d" % r(2, 0x0100))
	print("  link speed    0x0101 = %d" % r(2, 0x0101))
	print("  PLL locked    0x0200 = %d" % r(1, 0x0200))
	print("  FE power      0x0213 = %d" % r(2, 0x0213))
	print("  asic rx en    0x0318 = 0x%016X" % r(64, 0x0318))
	print("  deserializer  0x0302 = 0x%016X" % r(64, 0x0302))
	print("  decoder       0x0310 = 0x%016X" % r(64, 0x0310))
	print("  counters (mtx mrx mrxBad slaveOn stx srx srxBad):", c.getFEBDCount1(p, s))
for port in c.getActivePorts():
	print("port %d counts (tx rx rxBad):" % port, c.getPortCounts(port))
