list_ASIC = []
list_ASIC.append(0)
list_ASIC.append(2)

list_ALDO = ['A', 'B']

map_input = {}
for asic in list_ASIC:
    map_input[asic] = {}

list_rang = ['low', 'high']

for rang in list_rang:
    
    # map_input[0]['A'] = '../config/ALDO_T2TB_0005_0006_2022_09_30/prova_ASIC0_ALDO_A_%s.tsv'%rang
    # map_input[0]['B'] = '../config/ALDO_T2TB_0005_0006_2022_09_30/prova_ASIC0_ALDO_B_%s.tsv'%rang
    # map_input[2]['A'] = '../config/ALDO_T2TB_0005_0006_2022_09_30/prova_ASIC2_ALDO_A_%s.tsv'%rang
    # map_input[2]['B'] = '../config/ALDO_T2TB_0005_0006_2022_09_30/prova_ASIC2_ALDO_B_%s.tsv'%rang

    map_input[0]['A'] = '../config/2B/T2TB_0002_0003_HPK_2022_11_18/aldo_scan_ASIC0_ALDO_A_%s.tsv'%rang
    map_input[0]['B'] = '../config/2B/T2TB_0002_0003_HPK_2022_11_18/aldo_scan_ASIC0_ALDO_B_%s.tsv'%rang
    map_input[2]['A'] = '../config/2B/T2TB_0002_0003_HPK_2022_11_18/aldo_scan_ASIC2_ALDO_A_%s.tsv'%rang
    map_input[2]['B'] = '../config/2B/T2TB_0002_0003_HPK_2022_11_18/aldo_scan_ASIC2_ALDO_B_%s.tsv'%rang

    # map_input[0]['A'] = '../config/2B/T2TB_0002_0003_FBK_2022_10_24/aldoScan_ASIC0_ALDO_A_%s.tsv'%rang
    # map_input[0]['B'] = '../config/2B/T2TB_0002_0003_FBK_2022_10_24/aldoScan_ASIC0_ALDO_B_%s.tsv'%rang
    # map_input[2]['A'] = '../config/2B/T2TB_0002_0003_FBK_2022_10_24/aldoScan_ASIC2_ALDO_A_%s.tsv'%rang
    # map_input[2]['B'] = '../config/2B/T2TB_0002_0003_FBK_2022_10_24/aldoScan_ASIC2_ALDO_B_%s.tsv'%rang

  
    for aldo in list_ALDO:
        outFileName = 'aldo_scan_ALDO_%s_%s.tsv' %(aldo,rang)
        out = open(outFileName, 'w')
        
        for asic in list_ASIC:
            with open(map_input[asic][aldo], 'r') as f:
                for line in f:
                    print line
                    readings = line.split()
                    line_out = '0\t0\t%d\t%3d\t%f\n' %(asic,int(readings[0]),float(readings[1]))
                    out.write(line_out)
        out.close()
