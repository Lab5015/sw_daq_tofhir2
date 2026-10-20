# -*- coding: utf-8 -*-
"""
Dump a hardware-independent reference of what the petsys Python library computes,
so that the Python 2 (CentOS 7) and Python 3 (AlmaLinux 9) versions can be compared.

Run from the build directory (the one containing petsys/ and shm_raw):
    python2 /path/to/dump_reference.py ref_py2.txt [config.ini]    # CentOS 7
    python3 /path/to/dump_reference.py ref_py3.txt [config.ini]    # AlmaLinux 9
    diff ref_py2.txt ref_py3.txt

Works with both Python 2 and Python 3. No daqd and no hardware are needed:
the socket to daqd is replaced by a fake one that records what is sent.
"""
from __future__ import print_function
import sys, os, struct

sys.path.insert(0, os.getcwd())
from bitarray import bitarray
from petsys import tofhir2b, tofhir2x, daqd, config

out = open(sys.argv[1], "w")
def w(*args):
	out.write(" ".join([str(a) for a in args]) + "\n")

def hx(v):
	# hex() appends "L" to longs in py2
	return "0x%x" % v

def rp(v):
	# repr() that prints the same in py2 and py3 (sets are shown differently)
	if isinstance(v, (set, frozenset)):
		return "set" + repr(sorted(v))
	if isinstance(v, dict):
		return "{" + ", ".join(["%s: %s" % (rp(k), rp(v[k])) for k in sorted(v.keys(), key=repr)]) + "}"
	return repr(v)

def hexs(b):
	return " ".join(["%02X" % x for x in bytearray(b)])

# random.Random gives different sequences in py2 and py3: use a plain LCG
_lcg_state = [12345]
def _lcg_bit():
	_lcg_state[0] = (1103515245 * _lcg_state[0] + 12345) & 0x7FFFFFFF
	return (_lcg_state[0] >> 16) & 1

def pattern(n):
	# Deterministic bit pattern (same in py2 and py3)
	return bitarray("".join(["01"[_lcg_bit()] for i in range(n)]))

CLASSES = [ "AsicGlobalConfig", "AsicChannelConfig", "AsicGlobalConfigTX", "AsicGlobalConfigStatus" ]

#
# 1. ASIC configuration bit vectors
#
for mod in (tofhir2b, tofhir2x):
	for cname in CLASSES:
		cls = getattr(mod, cname)
		c = cls()
		tag = "%s.%s" % (mod.__name__.split(".")[-1], cname)
		w("== %s length %d" % (tag, len(c)))
		# Field-level defaults (immune to uninitialized gap bits in old bitarray)
		for key in sorted(c.getKeys()):
			w("default", tag, key, c.getValue(key))
		# setValue/getValue on a fully deterministic vector
		c = cls(pattern(len(c)))
		w("pattern", tag, c.to01())
		for key in sorted(c.getKeys()):
			n = len(c.fields[key])
			for v in sorted(set([0, 1, (2**n - 1) // 3, 2**n - 1, 2**n + 5])):
				c2 = cls(c)
				c2.setValue(key, v)
				w("set", tag, key, v, c2.getValue(key), c2.to01())

#
# 2. Command frames sent to daqd (fake socket)
#
class FakeSocket(object):
	def __init__(self):
		self.sent = []
		self.pending = b""
		self.reply_payload = None
	def send(self, data):
		data = bytes(data)
		self.sent.append(data)
		if len(self.sent) % 2 == 0:
			# Second send of a 0x05 command: raw frame; reply with 17 header bytes + payload
			raw = data
			payload = self.reply_payload(raw)
			frame = raw[0:17] + bytes(payload)
			self.pending = struct.pack("@H", len(frame)) + frame
		return len(data)
	def recv(self, n):
		r, self.pending = self.pending[:n], self.pending[n:]
		return r

def bare_instance(cls):
	# Create an instance without calling __init__ (which would connect to daqd)
	try:
		return cls.__new__(cls)
	except AttributeError:
		# Python 2 old-style class
		import types
		return types.InstanceType(cls)

conn = bare_instance(daqd.Connection)
sock = FakeSocket()
conn._Connection__socket = sock
conn._Connection__lastSN = 0x1234
conn._Connection__asic_module = tofhir2b
conn._Connection__hvdac_config_cache = {}

def last_frame():
	return sock.sent[-1]

# ASIC command: reply echoes back the written value, right-aligned as the ASIC does
def asic_reply(raw):
	cmd = bytearray(raw[19:])
	l = cmd[8] + 1
	bits = bitarray()
	bits.frombytes(bytes(cmd[9:]))
	nbytes = (l + 7) // 8
	padded = bitarray("0" * (8*nbytes - l)) + bits[0:l]
	return bytearray([0x00]) + bytearray(padded.tobytes())
sock.reply_payload = asic_reply

# Newer versions of the library pass a readID argument to the ASIC command
cmd_ll = conn._Connection__tofhir2_cmd_ll
_f = getattr(daqd.Connection._Connection__tofhir2_cmd_ll, "__func__", daqd.Connection._Connection__tofhir2_cmd_ll)
CMD_HAS_READID = "readID" in _f.__code__.co_varnames[:_f.__code__.co_argcount]
w("cmd_has_readid", CMD_HAS_READID)

for mod in (tofhir2b, tofhir2x):
	conn._Connection__asic_module = mod
	for cname, regID in [ ("AsicGlobalConfig", 32), ("AsicChannelConfig", 5), ("AsicGlobalConfigTX", 33) ]:
		cls = getattr(mod, cname)
		value = cls(pattern(len(cls())))
		for chipID in [0, 1, 7, 15]:
			busID = chipID // 2
			lChipID = chipID % 2
			if CMD_HAS_READID:
				status, reply = cmd_ll(0, 0, busID, lChipID, 2*busID+lChipID, regID, True, True, value)
			else:
				status, reply = cmd_ll(0, 0, busID, lChipID, regID, True, True, value)
			w("asiccmd", mod.__name__.split(".")[-1], cname, chipID, "frame", hexs(last_frame()))
			w("asiccmd", mod.__name__.split(".")[-1], cname, chipID, "status", status, "reply", reply.to01(), "eq", reply == value)

# Config register read/write
def reg_reply(raw):
	cmd = bytearray(raw[19:])
	if cmd[0] == 0x00:
		# read: n_words in cmd[1..2], one byte per word for config registers
		n_words = (cmd[1] | (cmd[2] << 8)) + 1
		return bytearray([0x00] + [ (0x5A + 17*k) & 0xFF for k in range(n_words) ] + [0x00])
	else:
		return bytearray([0x00])
sock.reply_payload = reg_reply

for width, addr, value in [ (1, 0x0000, 1), (16, 0x0012, 0xBEEF), (46, 0x0203, 0x123456789AB), (64, 0x0318, 0xAAAAAAAAAAAAAAAA) ]:
	conn.write_config_register(1, 2, width, addr, value)
	w("wrreg", width, hx(addr), hx(value), "frame", hexs(last_frame()))
	r = conn.read_config_register(1, 2, width, addr)
	w("rdreg", width, hx(addr), "frame", hexs(last_frame()), "value", hx(r))

# SPI / HV DAC command encoding
def spi_reply(raw):
	cmd = bytearray(raw[19:])
	return bytearray([0x00]) + cmd[19:]
sock.reply_payload = spi_reply
conn._Connection__activeFEBDs = { (0, 0) : (1, ), (0, 1) : (0, ) }
for channelID in [0, 5, 31, 32, 63]:
	for value in [0, 1, 1234, 2**14 - 1]:
		conn._Connection__write_hv_channel(0, 0, channelID, value, forceAccess=True)
		w("hv_ad5535", channelID, value, hexs(last_frame()))
for channelID in [0, 5, 15]:
	for value in [0, 1, 1234, 2**16 - 1]:
		conn._Connection__write_hv_channel(0, 1, channelID, value, forceAccess=True)
		w("hv_ltc2668", channelID, value, hexs(last_frame()))
w("prom_read", hexs(conn.read_hv_m95256(0, 1, 0x0000, 8)))

# Test pulse settings (rounding of fine phase)
captured = []
conn.write_config_register = lambda p, s, wd, a, v: captured.append((p, s, wd, a, v))
conn._Connection__asicConfigCache_TAC_Refresh = set()
conn.getActiveFEBDs = lambda: [ (0, 0) ]
for finePhase in [0.0, 0.5/336, 1.5/336, 2.5/336, 0.123, 1.0, 3.75]:
	del captured[:]
	conn.set_test_pulse_febds(100, 2048, finePhase, False)
	conn.setTestPulseBTL(finePhase, 0.25)
	w("testpulse", repr(finePhase), [ hx(c[4]) for c in captured ])

#
# 3. Calibration tables from a real config (optional)
#
if len(sys.argv) > 2:
	cfgFile = sys.argv[2]
	for name, mask in [ ("BIAS_CALIBRATION", config.LOAD_BIAS_CALIBRATION),
			    ("BIAS_SETTINGS", config.LOAD_BIAS_SETTINGS),
			    ("DISC_CALIBRATION", config.LOAD_DISC_CALIBRATION),
			    ("DISC_SETTINGS", config.LOAD_DISC_SETTINGS),
			    ("QDCMODE_MAP", config.LOAD_QDCMODE_MAP),
			    ("QDC_CALIBRATION", config.LOAD_QDC_CALIBRATION),
			    ("MAP", config.LOAD_MAP) ]:
		try:
			c = config.ConfigFromFile(cfgFile, loadMask=mask)
		except Exception as e:
			w("config", name, "not loaded:", type(e).__name__)
			continue
		for attr in sorted(vars(c).keys()):
			v = getattr(c, attr)
			if isinstance(v, dict):
				for k in sorted(v.keys()):
					w("config", name, attr, k, rp(v[k]))
			else:
				w("config", name, attr, rp(v))

		if mask == config.LOAD_BIAS_CALIBRATION:
			for key in sorted(c.getCalibratedBiasChannels()):
				for V in [ 0.5 * k for k in range(0, 121) ]:
					try:
						w("bias_dac", key, V, c.mapBiasChannelVoltageToDAC(key, V))
					except Exception as e:
						w("bias_dac", key, V, type(e).__name__)
		if mask == config.LOAD_DISC_CALIBRATION:
			for key in sorted(c.getCalibratedDiscChannels()):
				for vth in ["vth_t1", "vth_t2", "vth_e"]:
					for value in [0, 5, 20]:
						w("disc_dac", key, vth, value, c.mapAsicChannelThresholdToDAC(key, vth, value))
						# Newer versions also take a discriminator range
						for rng_ in [0, 1, 2]:
							try:
								w("disc_dac", key, vth, value, rng_, c.mapAsicChannelThresholdToDAC(key, vth, value, rng_))
							except TypeError:
								break

out.close()
print("Reference written to %s" % sys.argv[1])
