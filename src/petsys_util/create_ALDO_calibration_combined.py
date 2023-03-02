#!/usr/bin/env python
import argparse
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser("script to combine aldo config files")
    parser.add_argument("input_filenames", nargs="+", help="input filenames")
    parser.add_argument("--dest-dir", default='.', help="destination directory")
    args = parser.parse_args()

    output_filenames = set()

    map_input = {}
    for filename in args.input_filenames:
	head, tail = os.path.split(filename)
	root, ext = os.path.splitext(tail)
	print(root)
	asic = int(root.split('_')[2][-1])
	aldo = root.split('_')[-2]
	rang = root.split('_')[-1]

	output = os.path.join(args.dest_dir,'aldo_scan_ALDO_%s_%s.tsv' % (aldo,rang))

	if output in output_filenames:
	    print("appending to %s" % output)
	else:
	    print("writing to %s" % output)

	with open(output,"a" if output in output_filenames else "w") as out:
	    with open(filename, 'r') as f:
		for line in f:
		    readings = line.split()
		    line_out = '0\t0\t%d\t%3d\t%f\n' %(asic,int(readings[0]),float(readings[1]))
		    out.write(line_out)

	output_filenames.update((output,))
