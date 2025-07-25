#! /usr/bin/python

import sys
import time
import argparse

parser = argparse.ArgumentParser(description='Update configuration number') 
parser.add_argument("--major", dest="major", action="store_true", help="update major conf. # (e.g. 0.XY --> 1.XY") 
parser.add_argument("--minor", dest="minor", action="store_true", help="update minor conf. # (e.g. X.00 --> X.01") 
args = parser.parse_args()

f = open("/data1/cmsdaq/tofhir2/conf", "r")
conf = float(f.read())
f.close()

if args.major:
     conf += 1.
     conf = round(conf,0)

if args.minor:
     conf += 0.01

f = open("/data1/cmsdaq/tofhir2/conf", "w")
f.write("%.2f"%conf)
f.close()

print(conf)
