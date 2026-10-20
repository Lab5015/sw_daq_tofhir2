# Python 3 / AlmaLinux 9 port and firmware compatibility

This document summarizes the port of the TOFHiR2 DAQ software from Python 2 / CentOS 7 to Python 3 / AlmaLinux 9.
It also records what we learned about **FEB/D firmware versions and the software changes each one requires**.
Read that part before upgrading the firmware.

Last updated: 2026-10-19.

---

## 1. Overview

| | CentOS 7 (`pc-mtd-mib01`) | AlmaLinux 9 (`pc-mtd-tray`) |
|---|---|---|
| OS / Python | CentOS 7.9, Python 2.7.5 | AlmaLinux 9.7, Python 3.9 |
| Software | `~/DAQ/sw_daq_tofhir2b`, commit `42011d0` + local changes | this branch (Python 3 port of the same version) |
| FEB/D firmware | "old" firmware (`expect_reply = 0x01` protocol) | same firmware |
| Status | works | **works**: `init_system`, also with `--config config/2C/...` |

**Two** versions of the software were ported to Python 3, because they require different firmware (see §2):

| Branch | Based on | Required firmware |
|---|---|---|
| `tofhir2b-py3-alma9` | `42011d0` (CentOS 7 version) | firmware **currently** on the FEB/D |
| `tofhir2b-py3-alma9-newfw` | `9b03740` (GitHub `tofhir2b`, 2025-08-06) | **new** firmware (`firmware/febd_working.bin`, `firmware/adapter_working.bin`) |

### 1.1 Scripts edited inside `build/` on CentOS 7

On `pc-mtd-mib01` several scripts were edited **directly in `build/`** instead of in `src/`. CMake copies scripts from
`src/` into `build/` with `configure_file`, so the version actually used for data taking was not the one in git.
These `build/` versions were imported into `src/petsys_util/` on this branch (and then ported to Python 3):

| Script | Main difference from `src/` |
|---|---|
| `acquire_tdc_calibration` | test pulse interval `1024*2` instead of `1024`. **Needed for sensible TDC calibrations.** The same fix is in GitHub commit `f5a4915` "add 2x factor to get sensible tdc calibrations" |
| `acquire_qdc_calibration` | pandas-based fast QDC trimming, `--att` (required by `configuration.template.sh`) and `--trimE` options, interval `1024*2` in the main acquisition. **Needed for the QDC calibration.** |
| `acquire_sipm_data_scan`, `acquire_sipm_stressTest`, `scan_aldo_hv`, `create_ALDO_calibration_combined.py` | lab updates (2023–2026) |

The library in `build/petsys/` was identical to `src/petsys_py_lib/`.
`build/` on CentOS 7 also contains lab scripts that are not in git and were **not** imported:
`scannone_launcher.py`, `scannone_converter.py`, `scannone_mapper.py`, `scannone_README.md`, `convert_TB.py`,
`renameCalibs.py`, `convert_many.sh`, `acquire_tp_basic`, `acquire_sipm_data_scan_temp`, `lancia_*`, `drawIVMerged.py`.

**Rule for the future:** edit scripts in `src/`, then run `make` (it copies them into `build/`).

---

## 2. Firmware versions and required software changes

### 2.1 The two development lines

- **CentOS 7, `42011d0`** (July 2025): local `cmsdaq` branch, based on Ricardo Bugalho's TOFHiR 2C support
  (`fada0c1 Add support for TOFHiR 2C`). This commit is **not on GitHub**: after the merge base `fada0c1` the GitHub
  history was rewritten.
- **GitHub `tofhir2b`, `9b03740`** (6 August 2025): contains "getting Ricardo's latest version" (`5d6a0c3`) and
  "Latest working firmware" (`9b03740`, which adds `febd_working.bin` and `adapter_working.bin`). It has the same commit
  messages as the CentOS 7 line but different hashes: it is a rewritten history, not a descendant of `42011d0`.

The `daqd` C++ code (`src/daqd/`) is **identical** in both versions. What differs is the Python library (`daqd.py`,
`config.py`, new tester modules) and some C++ analysis programs.

### 2.2 The breaking difference: the ASIC configuration command

In `src/petsys_py_lib/daqd.py`, function `__tofhir2_cmd_ll`, the second byte of the command sent to the FEB/D:

```python
# Current firmware (CentOS 7 version, 42011d0)
composed_command = bytearray([ busID,
        expect_reply and 0x1 or 0x0,               # <-- "reply expected" flag in bit 0
        0x00, 0x2F, 0xAF, 0xC1, chipID, (write and 0x80 or 0x00) | regID, l-1 ]) + payload

# New firmware (GitHub version, 9b03740)
composed_command = bytearray([ busID,
        (expect_reply and 0x80 or 0x00) | readID,  # <-- flag in bit 7, readID = 2*busID + chipID in the low bits
        0x00, 0x2F, 0xAF, 0xC1, chipID, (write and 0x80 or 0x00) | regID, l-1 ]) + payload
```

With the **new software on the old firmware**, the firmware reads bit 0 as the "reply expected" flag:
- for ASIC 0 (`readID = 0`) bit 0 is 0: configuration reads return **only the status byte, no data**
  (`ConfigurationErrorReplyLength: expected 32 bytes, got 0 bytes`), and the ASIC shows "config link: FAIL";
- for ASIC 1 (`readID = 1`) bit 0 is 1: even the TX configuration (which expects no reply) waits for an ACK.
  If the ASIC is absent: `ConfigurationErrorStatus: Error 0xe2 when configuring ASIC at port 0, slave 0, bus 0, chip 01`.

**Typical symptom of software/firmware mismatch:** `init_system` stops with `Error 0xe2` on chip 01, or completes with
"0 active ASICs" and "config link: FAIL". Neither Python nor `daqd` is at fault: the original Python 2 code gives the
same error. We verified that the GitHub py2 code fails the same way on CentOS 7 too.

### 2.3 Other `daqd.py` differences between the two versions

Apply/check these together with §2.2 when moving to the new firmware:

| Item | CentOS 7 version (current fw) | GitHub version (new fw) |
|---|---|---|
| ASIC command signature | `__tofhir2_cmd(p, s, bus, chip, regID, ...)` | `__tofhir2_cmd(p, s, bus, chip, readID, regID, ...)`, `readID = 2*busID + lChipID` |
| ASICs scanned per FEB/D | `range(8)` | `range(16)` |
| e-fuse loading | writes `0x0213 = 0b111` before and `0b011` after | no writes to `0x0213` |
| ASICs in inconsistent state | `raise ErrorAsicPresenceInconsistent` | ignored (`pass`) |
| `read_mem_ctrl` | `n_bytes_per_addr = ceil(addr_width/8)` | `n_bytes_per_addr = 2` |
| FE power on | direct write to `0x0213` | `set_fe_power()` |
| Extra functions | — | `i2c_master`, `acquireAsBytes/acquireAsPandas` (numpy/pandas), `.modf` file with `attGain` column |
| `config.py` | — | `loadToHardware(..., att=4)`, `mapAsicChannelThresholdToDAC(..., disc_range)` |
| `SystemConfig.cpp` | — | `att` parameter (QDC table per attenuation) |
| Extra modules | — | `tests.py`, `fe_tester.py`, `bga_tester.py`, `tester_controller.py`, `spi.py`, `i2c.py` |

### 2.4 Procedure for a future firmware upgrade

1. Program the FEB/D and the adapter with the files in `firmware/` from the GitHub version (`febd_working.bin`,
   `adapter_working.bin`). **Warning:** after the upgrade the CentOS 7 software (and this branch) will no longer work
   with the board.
2. Use the `tofhir2b-py3-alma9-newfw` branch (Python 3 port of `9b03740`, already validated, see §5) and build it as in §3.
3. With `daqd` running, from `build/` run:
   - `python3 ../tools/py3_check/diag_febd.py`: reads registers only (system mode, links, PLL, detected ASICs);
   - `python3 ../tools/py3_check/diag_asic0.py`: reads, writes and reads back the configuration of ASIC 0.
     With matching software and firmware, reads return 32 bytes and `matches default: True`.
4. Then `./init_system`. Expected on the single-ASIC board: "FEB/D (0, 0) has 1 active ASICs: 0".
5. If there are local changes to carry over (configurations, lab scripts), compare the files listed in §2.3.
   The Python 3 fixes are the same in both branches.

### 2.5 FEB/D register state (reference, current firmware)

Read with `diag_febd.py` on `pc-mtd-tray` (board with ASIC 0 only):

```
system mode   0x0104 = 0x0004   (TOFHiR 2C; set_system_mode --mode tofhir2c)
asic type     0x0102 = 0x0004
febd type     0x0022 = 0x0000
n links-1     0x0100 = 0
link speed    0x0101 = 1         (DDR)
PLL locked    0x0200 = 1
deserializer  0x0302 = 0x...0001 (ASIC 0 only)
decoder       0x0310 = 0x...0001
```

The FEB/D is reached over UDP at `192.168.1.25:2000`. On `pc-mtd-tray` it is connected through a USB Ethernet adapter
(`enp1s0f0u2u2`, `192.168.1.100/24`). It does not answer ping, which is normal.
The `daqd` message `Mismatched SN: sent ..., got feff` at startup is harmless: it is the late reply to the probe packet
sent by the `UDPFrameServer` constructor, and it is discarded.

---

## 3. Installing and building on AlmaLinux 9

```bash
sudo sh INSTALL_SW_REQUIREMENTS_ALMA9.sh      # EPEL + CRB, boost, ROOT, python3-*, pip install bitarray pandas
mkdir build && cd build && cmake .. && make
source daqd.sh                                # starts daqd --daq-type GBE
./init_system --config ../config/2C/config_ith1_attGain0.ini
```

Notes:
- **Python version:** AlmaLinux 9 Boost.Python (`libboost_python39`) and `python3-root` are built for the system
  Python 3.9, i.e. `python3`. If Python 3.11 is also installed, CMake would pick it and the build would fail
  (`boost_python311Config.cmake` not found). This is why `CMakeLists.txt` uses the `python3` found in `PATH`.
  Another interpreter can be forced with `cmake -DPython3_EXECUTABLE=...`.
- If a CMake configuration fails, delete the `build` directory before retrying: the cache persists.
- `bitarray` and `pandas` are not RPM packages on EL9: they are installed with pip.
- **`root-minuit` is required** (in the install script). Without it ROOT cannot create the `Minuit` and `Linear`
  minimizers, every fit in `process_tdc_calibration` fails silently and the TDC calibration is empty
  (`Could not create the Linear minimizer`, then `WARNING: M (-1.0) is out of range` for every TAC, and a
  `tdc_calibration.tsv` with only the header line).
- **Minimizer:** ROOT 6.40 defaults to Minuit2, ROOT 6.24 (CentOS 7) to Minuit. With Minuit2 the TDC fits converge
  to different minima (t0/a0/a2 off by tens of %). `process_tdc_calibration` and `process_qdc_calibration` now call
  `ROOT::Math::MinimizerOptions::SetDefaultMinimizer("Minuit")`. With this, on the same raw data as CentOS 7
  (`config/2C_HYPER`, 2026-10-19): QDC table identical (232 entries), TDC table 510/512 TACs within 0.1%.
- The PCIe kernel driver (`src/kernel/psdaq.c`) was **not** ported. It is not needed with the Ethernet DAQ
  (`--daq-type GBE`), and it does not compile on the AlmaLinux 9 kernel (`class_create`, `dev_uevent`).
  `daqd` still builds because it only uses the driver header.

---

## 4. What was changed

### 4.1 Python (`src/petsys_py_lib` library, `src/petsys_util` scripts, GUI, TBScripts)

Automatic pass:
- `2to3` (print, `raw_input`, dict methods, `ConfigParser`, imports);
- indentation: 12+ files mixed tabs and spaces (Python 2 treated a tab as 8 columns, Python 3 raises `TabError`).
  They were normalized, checking that the AST is identical to what Python 2 saw;
- shebangs unified to `#!/usr/bin/env python3` (there is no `python` on AlmaLinux 9).

Manual fixes (errors that Python 3 does not report, but that produce wrong data):
- **bytes/str in the protocol with `daqd`:** in Python 3 `str(bytearray)` produces the text `"bytearray(b'...')"`.
  It was used to build *every* command frame (`sendCommand`) and to decode the ASIC readback
  (`tmp.frombytes(str(reply))`). Now `bytes(...)` is used. Also fixed: the shared memory name (`.decode()`), the HV
  EEPROM (`read/write_hv_m95256`, comparison with `b"PETSYS  "`), the trigger mask (`config.py`) and the GUI pipes.
- **integer division** (`/` → `//`): bus/chip/port indices, `bs/2` on the shared memory pointers (a float made
  `struct.pack` fail), `getCurrentTimeTag() // 1024`, `simultaneousChannels` in `acquire_qdc_calibration`
  (it would have been 2.5 instead of 2 in Python 3), injector amplitude in the tests.
- **rounding:** Python 3 `round()` rounds halves to even (2.5 → 2), Python 2 rounded them away from zero.
  For the test pulse fine phase and the bias → DAC interpolation, `round_half_away()` was added to reproduce the
  Python 2 behaviour (same DAC values).
- **bitarray ≥ 1.0:** `__new__` no longer accepts `initial=`. `AbstractConfig.__new__` in `tofhir2.py` restores it
  (before, `deepcopy` and the `AsicGlobalConfig(initial=...)` constructors failed).
- `from string import upper` (does not exist in Python 3), `ord()` on bytes, `is` used to compare literals,
  regexes without `r""`.
- **pandas** (0.17 on CentOS 7, 2.3 on AlmaLinux 9): in `acquire_qdc_calibration` `aggfunc=[np.sum, len]` became
  `["sum", len]` (same result; `np.sum` raises a FutureWarning in recent pandas). The trimming logic
  (`pivot_table`/`concat`/`unstack` and stop conditions) gives identical results with both versions on synthetic data.
  pandas `/` was already true division in Python 2.
- **TBScripts:**
  - H4DAQ run control: with pyzmq in Python 3 `recv()` returns bytes, so `message == "WE\0"` was always false and
    the spill loop never started. Now `send_string`/`recv_string` are used;
  - `TXP3510P` serial: added a text↔bytes adapter;
  - `Lab5015_utils`: added the missing `serialClient` import.

### 4.2 C++ and build
- `CMakeLists.txt`: `find_package(Python3)` and Boost `python39`, policy CMP0167, choice of `python3`,
  `BOOST_BIND_GLOBAL_PLACEHOLDERS` for `shm_raw_py`.
- `INSTALL_SW_REQUIREMENTS_ALMA9.sh`: new install script (tested in an AlmaLinux 9 container).
- `SystemConfig.cpp`: `const char*` for iniparser 4 (CentOS 7 version only; already fixed in the GitHub version).
- `convert_raw_to_event.cpp`, `convert_raw_to_trigger.cpp`: added `#include <iostream>` (gcc 11).
- `FrameServer.cpp`, `DAQFrameServer.cpp`: added the missing `return` in non-void functions
  (undefined behaviour with gcc 11).
- `shm_raw_py.cpp`: free the buffer in `events_as_bytes` (memory leak).
- `process_tdc_calibration.cpp`, `process_qdc_calibration.cpp`: use the Minuit minimizer as on CentOS 7 (see §3).

### 4.3 Pre-existing Python 2 bugs, fixed
- `fe_tester.py`: on over-current, the warning `print` raised an exception **before** the UUT power was switched off.
- `spi.tmp126_ll`: parameter had the wrong name.

### 4.4 Pre-existing Python 2 bugs, **not** fixed (good to know)
- `acquire_sipm_data` with `--paramTable`: uses `asicsConfig` without defining it.
- `TBScripts/run_tofhir_h4daq_old.py`: syntax error (`,,`).
- `UDPFrameServer.cpp`: `errno = EAGAIN` (assignment instead of comparison) and the `timedwait` timeout computed with
  `1e8` instead of `1e9`. Both are harmless in current use.
- Other undefined names in secondary scripts (`change_calibration_topology`, `tester_scan_aldo`, `start_gui`).

---

## 5. Validation

The tool is `tools/py3_check/dump_reference.py`, which runs with both Python 2 and Python 3. Without hardware, it
exercises the library and writes to a file:
- ASIC configuration vectors and the encoding/decoding of every field;
- the frames sent to `daqd`, through a fake socket;
- registers and HV DACs;
- the test pulse fine phase;
- calibration table parsing and the V → DAC and threshold → DAC conversions.

```bash
# from the build directory (or any directory containing petsys/)
python2 dump_reference.py ref_py2.txt [config.ini]   # CentOS 7, original code
python3 dump_reference.py ref_py3.txt [config.ini]   # AlmaLinux 9, ported code
diff ref_py2.txt ref_py3.txt
```

Results (original py2 code run in a CentOS 7 container with Python 2.7.5 and bitarray 0.8.3):

| Version | Lines compared | Differences |
|---|---|---|
| CentOS 7 (`42011d0`) | 4125 | **0** |
| GitHub (`9b03740`) | 5853 | **0** |

In addition:
- 256 variants of the TX configuration command compared bit by bit between py2 and py3: identical;
- full build with no errors or warnings on AlmaLinux 9 (host and container);
- **hardware test** (`pc-mtd-tray`, FEB/D with ASIC 0 only): `init_system` and
  `init_system --config config/2C/config_ith1_attGain0.ini` work.

---

## 6. To do / good to know
- TBScripts instruments (Keithley, TEC, PiLas, TXP3510P, H4DAQ): ported but **not tested** with the real instruments.
- `acquire_sipm_IV_scan`, `scan_aldo_hv` and `acquire_sipm_stressTest` import `Lab5015_utils` from
  `/home/cmsdaq/Programs/Lab5015Utils/`, outside this repository: that copy needs to be checked separately.
- The GUI (`start_gui`) must be launched from its own directory. It was not tested on hardware.
- Probably unused files: `src/petsys_py_lib/tofhir2_common.py` (duplicate of `tofhir2.py`),
  `src/petsys_util/start_gui` (the installed one is `src/gui/start_gui`), `TBScripts/*_old.py`,
  `TBScripts/acquire_sipm_IV_scan_K2000` (duplicate of the `.py`), `src/petsys_py_lib/tofpet2b.py` and `tofpet2c.py`
  (not installed).
- The old `INSTALL_SW_REQUIREMENTS_CENTOS.sh` was left unchanged.
