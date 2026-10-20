#!/bin/sh
# Software requirements for AlmaLinux 9 (Python 3)
# Run as root: sudo sh INSTALL_SW_REQUIREMENTS_ALMA9.sh
set -e

dnf -y install epel-release dnf-plugins-core
dnf config-manager --set-enabled crb

dnf -y install gcc \
gcc-c++ \
make \
cmake \
boost-devel \
boost-python3 \
iniparser-devel \
root \
root-gui-fitpanel \
root-spectrum \
root-spectrum-painter \
root-minuit \
root-minuit2 \
root-fumili \
root-physics \
root-multiproc \
python3 \
python3-devel \
python3-pip \
python3-root \
python3-numpy \
python3-pyserial \
python3-gobject \
gtk3 \
xterm

# Not packaged for EL9
python3 -m pip install bitarray pandas

# The PCIe DAQ card (PFP_KX7) driver is not needed when using the
# Ethernet DAQ (daqd --daq-type GBE), and is not built on AlmaLinux 9.
