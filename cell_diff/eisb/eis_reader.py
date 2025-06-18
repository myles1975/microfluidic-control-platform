# -*- coding: utf-8 -*-
"""
Created on Thu Apr 25 09:26:45 2019

@author: joeld
"""
import numpy as np
import matplotlib.pyplot as plt

def read_eis(filepath):
    metadata = {}
    data = []
    
    with open(filepath, 'r') as f:
        header = f.readline()
        for pair in header.split(','):
            key, value = pair.split(':',1)
            metadata[key.strip()] = value.strip()
        f.readline()
        f.readline() # F,R,I or T,F,R,I as of AD5933 version 1.3
        for line in f:
            if line:
                data.append([float(d) for d in line.split(',')])
    return metadata, data

def data_to_array(data, sweep=True):
    averaged = [[],[],[],[]]
    if sweep:
        # data may be repeated for a given frequency - regroup by frequency
        by_freq = {}
        for row in data: # row is [T,F,R,I]
            if row[1] in by_freq:
                by_freq[row[1]][0].append(row[0])
                by_freq[row[1]][1].append(row[2])
                by_freq[row[1]][2].append(row[3])
            else:
                by_freq[row[1]] = [[row[0]],[row[2]],[row[3]]]
        # average each frequency
        for freq in sorted(by_freq):
            averaged[0].append(np.average(np.array(by_freq[freq][0])))
            averaged[1].append(freq)
            averaged[2].append(np.average(np.array(by_freq[freq][1])))
            averaged[3].append(np.average(np.array(by_freq[freq][2])))
    else: # single frequency
        for row in data:
            for i,d in enumerate(row):
                averaged[i].append(d)

    averaged = np.array(averaged)
    
    # calculate other useful data from real and imaginary parts
    # freq, real, imag, mag, phase
    structure = np.dtype({'names':('T','F','R','I','M','P'),
                          'formats':(np.float64, np.float64,np.float64,
                                     np.float64, np.float64,np.float64)})
    d = np.zeros(averaged.shape[1], dtype=structure)
    d['T'] = averaged[0]
    d['F'] = averaged[1]
    d['R'] = averaged[2]
    d['I'] = averaged[3]
    d['M'] = np.sqrt(d['R']**2+d['I']**2)
    d['P'] = np.arctan2(d['I'],d['R'])
    return d

def read_eis_to_array(filepath, sweep=True):
    m,d = read_eis(filepath)
    return m,data_to_array(d, sweep)

def calibration_to_poly(filename, Rcal=56.2e3):
    cal = data_to_array(read_eis(filename)[1])
    return np.poly1d(np.polyfit(cal['F'],cal['M'],1)*Rcal)

def calibrate_poly(data, p):
    return p(data['F']) / data['M']

def calibrate(cal,data,Rcal=56.2e3):
#    gf = (1/Rcal)/cal['M']
#    data['M'] = 1/(gf*data['M'])
#    return data
    data['M'] = Rcal*cal['M']/data['M']
    data['P'] -= cal['P']
    
if __name__ == '__main__':
    #TODO setup command line to read a file in from argv
    pass
#    plt.close('all')
#    
#    filebase = r'C:\Users\joeld\Documents\EIS_data\2019_07_03'
#    filename = r'saline_test_15k_rfb'
#    m0,cal0 = read_eis(r'{}\{}_cal_0.txt'.format(filebase,filename))
#    m0,d0 =   read_eis(r'{}\\{}_dat_0.txt'.format(filebase,filename))
#    m1,cal1 = read_eis(r'{}\\{}_cal_1.txt'.format(filebase,filename))
#    m1,d1 =   read_eis(r'{}\\{}_dat_1.txt'.format(filebase,filename))
#    cal0 = data_to_array(cal0)
#    cal1 = data_to_array(cal1)
#    
#    d0 = data_to_array(d0)
#    d1 = data_to_array(d1)
#    
#    calibrate(cal0,d0)
#    calibrate(cal1,d1)
#    
#    f,a = plt.subplots()
#    a.plot(d0['F'],d0['R'],label='d0 R')
#    a.plot(d1['F'],d1['R'],label='d1 R')
#    a.plot(d0['F'],d0['I'],label='d0 I')
#    a.plot(d1['F'],d1['I'],label='d1 I')
#    a.plot(d0['F'],d0['M'], label='d0 - 100k')
#    a.plot(d1['F'],d1['M'], label='d1 - 22k')


#    gf0 = 56.2e3*cal0['M']
#    gf1 = 56.2e3*cal1['M']
    
#    a.plot(d0['F'],gf0/d0['M'], marker='x', label='d0 - 100k')
#    a.plot(d1['F'],56.2e3*cal0['M']/d0['M'], marker='o', label='d1 - 22k',fillstyle='none')
#    a.plot(cal0['F'],gf0/cal0['M'], marker='|', label='cal0')
#    a.plot(cal1['F'],gf1/cal1['M'], marker='^', label='cal1',fillstyle='none')
#    a.plot(d0['F'],d0['R'], label='d0 - 22k')
#    a.plot(d1['F'],d1['R'], label='d1 - 100k')
#    a.plot(cal0['F'],cal0['R'], label='cal0')
#    a.plot(cal1['F'],cal1['R'], label='cal1')
#    a.legend()
    
#    f1,a1 = plt.subplots()
#    gf0 = (1/56.2e3)/cal0['M']
#    a1.plot(d0['F'], 1/(gf0*d0['M']))
#    test_file = r'C:\Users\joeld\Documents\EIS_data\2019_07_09\10k_single_freq_run2_dat_0.txt'
#    m,x = read_eis_to_array(test_file, sweep=False)
#    
#    f,a = plt.subplots()
#    print(x['T'])
#    a.plot(x['T'],x['P'])
