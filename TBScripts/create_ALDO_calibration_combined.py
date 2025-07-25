list_ASIC = []
list_ASIC.append(0)
list_ASIC.append(2)

#list_ALDO = ['A']
#list_ALDO = ['B']
list_ALDO = ['A','B']

map_input = {}
for asic in list_ASIC:
    map_input[asic] = {}


map_input[0]['A'] = '../config/aldo_scan_ASIC0_ALDOA.txt'
map_input[0]['B'] = '../config/aldo_scan_ASIC0_ALDOB.txt'
map_input[2]['A'] = '../config/aldo_scan_ASIC2_ALDOA.txt'
map_input[2]['B'] = '../config/aldo_scan_ASIC2_ALDOB.txt'


for aldo in list_ALDO:
    outFileName = '../config/aldo_scan_ALDO_%s.tsv' % aldo 
    out = open(outFileName, 'w')
    
    for asic in list_ASIC:
        with open(map_input[asic][aldo], 'r') as f:
            for line in f:
                print line
                readings = line.split()
                line_out = '0\t0\t%d\t%3d\t%f\n' %(asic,int(readings[0]),float(readings[1]))
                out.write(line_out)
    out.close()
