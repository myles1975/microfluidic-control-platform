# -*- coding: utf-8 -*-
"""
Created on Thu May 16 13:21:19 2019

@author: joeld
"""
import os, re
import matplotlib.pyplot as plt
import numpy as np
from eis_reader import read_eis_to_array

def find_files(base_dir, names, skip_first=False):
    files = []
    for name in names:
        pattern = re.compile(name+r'_ch(\d)_(\d+)\.txt')
        for filename in os.listdir(base_dir):
            match = re.match(pattern, filename)
            if match:
                ch, i = int(match.group(1)), int(match.group(2))
                if skip_first and i==0:
                    continue
                files.append((os.path.join(base_dir, filename),ch,i))
    files.sort(key=lambda x: (x[0],x[1]))
    return files

def build_data(files):
    data = [[] for _ in set([c[1] for c in files])]
    for f in files:
        _, d = read_eis_to_array(f[0], sweep=True)
        data[f[1]].append(d)    
    return data

def build_sweeps(files):
    sweeps = data_sweeps()
    for data_file, ch, i in files:
        _,d = read_eis_to_array(data_file, sweep=True)
        sweeps.add_sweep(d,ch,i)
    return sweeps

def average_data(data):
    d0 = data[0][0]
    avg = [np.zeros(d0.shape, dtype=d0.dtype) for _ in data]
    for ch_dat, ch_avg in zip(data, avg):
        for col in d0.dtype.names:
            dat = []
            for ch in ch_dat:
                dat.append(ch[col])
            ch_avg[col] = np.average(np.array(dat), axis=0)
    return avg

def average_array(arrays):
    '''averages a list of matched structured arrays'''
    d0 = arrays[0]
    avg = np.zeros(d0.shape, dtype=d0.dtype)
    for col in d0.dtype.names:
        dat = []
        for a in arrays:
            dat.append(a[col])
        avg[col] = np.average(np.array(dat), axis=0)
    return avg

def process_calibration(base_dir, calibrations, plot=True):
    cal_files = find_files(base_dir, calibrations)
    
    cal_data = build_data(cal_files)
    cal_avg =  average_data(cal_data)
    
    cal_sweeps = build_sweeps(cal_files)
    
    cal_fit = [np.poly1d(np.polyfit(ca['F'],ca['M'],1)) for ca in cal_avg]
    
    if plot:
        fig, ax = plt.subplots(ncols=2)
        ax[0].set_title('All Calibration Sweeps')
        ax[0].set_xlabel('Frequency (Hz)')
        for i, ch in enumerate(cal_data):
            for d in ch:
                ax[0].plot(d['F'],d['M'],'C'+str(i)+':')
                ax[1].plot(d['F'],d['P'],'C'+str(i)+':')
        for i, (ch,fit) in enumerate(zip(cal_avg, cal_fit)):
            ax[0].plot(ch['F'], ch['M'],label='Average Channel '+str(i),
                    linewidth=3,color='C'+str(i),linestyle='--')
#            ax.plot(ch['F'], fit(ch['F']),label='Fit Channel '+str(i),
#                    linewidth=3,color='C'+str(i))
        ax[0].legend()
    return cal_avg, cal_fit, cal_sweeps

def process_data(base_dir, data_name, skip_first=True):
    data_files = find_files(base_dir, [data_name], skip_first=skip_first)
    sweeps = build_sweeps(data_files)
    return sweeps
        
def process_saline(base_dir, saline_names):
    saline_files  = find_files(base_dir, saline_names)
#    saline_data   = build_data(saline_files)
    saline_sweeps = build_sweeps(saline_files)
    return saline_sweeps

def process_main3(base_dir, calibrations, data_name, salines, plot_cal=True):
    # read in calibration tests
    cal_avg, cal_fit, cal_sweeps = process_calibration(base_dir, calibrations, plot_cal)
    dat_sweeps = process_data(base_dir, data_name)
    sal_sweeps = process_saline(base_dir, salines)
    cal_sweeps.calibrate(cal_avg)
    dat_sweeps.calibrate(cal_avg)
    sal_sweeps.calibrate(cal_avg)
            
    return cal_avg, cal_sweeps, dat_sweeps, sal_sweeps

class data_sweeps():
    
    def __init__(self):
        self.channel = []
        self.iteration = []
        self.data = {} # dict of list of arrays
        self.sweeps = [] # list of structured arrays
        
    def add_sweep(self, sweep, channel, iteration):
        self.channel.append(channel)
        self.iteration.append(iteration)
        self.sweeps.append(sweep)
#        if not self.data:
#            for key in sweep.dtype.names:
#                self.data[key] = []
#        for key in sweep.dtype.names:
#            self.data[key].append(sweep[key])
#            
#    def data_to_array(self):
#        '''call after all sweeps are added'''
#        for key in self.data:
#                for i, ch in enumerate(self.data[key]):
#                    self.data[key][i] = np.array(ch)
    
    def calibrate(self, cal_avg, Rcal=56.2e3):
        for i, ch in enumerate(cal_avg):
            for j, sweep in enumerate(self.sweeps):
                if self.channel[j] == i:
                    self.sweeps[j]['M'] = Rcal*ch['M']/sweep['M']
                    self.sweeps[j]['P'] -= ch['P']
            
    
    def calibrate_fit(self, cal_fit, Rcal=56.2e3):
        # TODO need to fit phase too
        for i, ch in enumerate(cal_fit):
            for j, sweep in enumerate(self.sweeps):
                if self.channel[j] == i:
                    self.sweeps[j]['M'] = Rcal*ch(sweep['F'])/sweep['M']
                    
    def filter_group(self, i, ch, mod=3):
        group = []
        for j, sweep in enumerate(self.sweeps):
            if self.channel[j] == ch and self.iteration[j]%mod == i:
                group.append(sweep)
        return group
    
    def average_groups(self, ch, mod=3):
        #TODO debug
        groups = np.array([self.filter_group(i, ch, mod) for i in range(mod)])
        avgs = np.average(groups, axis=1)
        stdevs = np.std(groups, axis=1)
        return avgs, stdevs
                    

def plot_sweeps(sweep, labels, logZ=True, sites=('cells','control')):
    fig, ax = plt.subplots(ncols=2, figsize=(10,4))
    mod = len(labels)
    plot_labels = []
    for i, data in enumerate(sweep.sweeps):
        cycle = i%mod
        label='{}, {}'.format(sites[1] if sweep.channel[i] else sites[0],
                                   labels[cycle])
        if label in plot_labels:
            label=None
        else:
            plot_labels.append(label)
        
        ax[0].plot(data['F'], data['M']/1000, 
                  linestyle = '-' if sweep.channel[i] else ':',
                  color='C'+str(cycle), label=label)
        ax[1].plot(data['F'], data['P'],
                  linestyle = '-' if sweep.channel[i] else ':',
                  color='C'+str(cycle), label=label)
    for a in ax: 
        a.set_xscale('log')
        a.set_xlabel('Frequency (Hz)')
        a.legend()
    if logZ:
        ax[0].set_yscale('log')
    ax[0].set_ylabel(r'|Z| (k$\Omega$)')
    ax[1].set_ylabel(r'$\angle$Z (rad)')
    
    fig.tight_layout()
    return fig, ax
    
def plot_groups(sweep, grp,title='', sites=('Cells','Control')):
    ch0 = sweep.filter_group(grp,0)
    ch1 = sweep.filter_group(grp,1)
    
    fig,ax = plt.subplots()
    for i, cells in enumerate(ch0):
        ax.plot(cells['F'],cells['M']/1000,'C0-',label=None if i else sites[0])
    for i,ctrls in enumerate(ch1):
        ax.plot(ctrls['F'],ctrls['M']/1000,'C1-',label=None if i else sites[1])
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('|Z| (k$\Omega$)')
    ax.legend()
    if title:
        ax.set_title(title)
    fig.tight_layout()      

def plot_channels(sweep,ch,groups=('DMSO control','50uM 2-APB','200uM 2-APB'),
                  title='', average=False):
    data = {grp:sweep.filter_group(i,ch,mod=len(groups)) for i,grp in enumerate(groups)}
        
    fig,ax = plt.subplots()
    ax2 = ax.twinx()
    for i, grp in enumerate(groups):
        if average:
            # assume matching frequency points
            datsM = np.array([dat['M'] for dat in data[grp]])
            avgM = np.average(datsM, axis=0)
            stdM = np.std(datsM, axis=0)
            datsP = np.array([dat['P'] for dat in data[grp]])
            avgP = np.average(datsP, axis=0)
            stdP = np.std(datsP, axis=0)
            f = data[grp][0]['F']
            ax.errorbar(f, avgM/1000, yerr=stdM/1000, 
                        fmt='C{}-'.format(i), label=grp)
            ax2.errorbar(f, avgP, yerr=stdP, fmt='C{}--'.format(i))
#            ax.plot(data[grp][0]['F'], avgM/1000, 'C{}-'.format(i),label=grp)
        else:
            for j, dat in enumerate(data[grp]):
                ax.plot(dat['F'],dat['M']/1000,'C'+str(i)+'-',
                        label=None if j else grp)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('|Z| (k$\Omega$)')
    ax.legend()
    if title:
        ax.set_title(title)
    else:
        ax.set_title('Channel {}'.format(ch))
    fig.tight_layout()    

def six_measurement_extraction(sweeps, saline):
    saline_tst  = average_array(saline.filter_group(0,0,1))
    saline_ctl  = average_array(saline.filter_group(0,1,1)) 
    control_tst = average_array(sweeps.filter_group(0,0,3))
    control_ctl = average_array(sweeps.filter_group(0,1,3))
    blocker_tst = average_array(sweeps.filter_group(2,0,3)) # 50uM 2-APB
    blocker_ctl = average_array(sweeps.filter_group(2,1,3))
    
    za = saline_ctl[ 'M']*np.exp(1j*saline_ctl[ 'P'])
    zb = saline_tst[ 'M']*np.exp(1j*saline_tst[ 'P'])
    zc = control_ctl['M']*np.exp(1j*control_ctl['P'])
    zd = control_tst['M']*np.exp(1j*control_tst['P'])
    ze = blocker_ctl['M']*np.exp(1j*blocker_ctl['P'])
    zf = blocker_tst['M']*np.exp(1j*blocker_tst['P'])
    
    z3 = zd-zb
    z5 = zf-zb
    z3pz4 = zc-za
    z5pz6 = ze-za
    cells_control = z3pz4*z3/(z3-z3pz4)
    cells_blocker = z5pz6*z5/(z5-z5pz6) 
    return cells_control, cells_blocker

def calc_cell_impedance(saline_ctl, saline_tst, control_ctl, control_tst,
                        blocker_ctl, blocker_tst):
    za = saline_ctl[ 'M']*np.exp(1j*saline_ctl[ 'P'])
    zb = saline_tst[ 'M']*np.exp(1j*saline_tst[ 'P'])
    zc = control_ctl['M']*np.exp(1j*control_ctl['P'])
    zd = control_tst['M']*np.exp(1j*control_tst['P'])
    ze = blocker_ctl['M']*np.exp(1j*blocker_ctl['P'])
    zf = blocker_tst['M']*np.exp(1j*blocker_tst['P'])
    
    z3 = zd-zb
    z5 = zf-zb
    z3pz4 = zc-za
    z5pz6 = ze-za
    cells_control = z3pz4*z3/(z3-z3pz4)
    cells_blocker = z5pz6*z5/(z5-z5pz6) 
    return cells_control, cells_blocker

if __name__ == '__main__':
    
    import sys
    plt.close('all')
    
    x,c,d,s = process_main3(sys.argv[1], #data directory
                        ['cal_pre','cal_post'],'test',
                        ['saline_pre','saline_post'])
    plot_sweeps(d, ('dmso control','50 uM 2-APB','200 uM 2-APB'))
    plot_sweeps(c, ('calibration',), logZ=False)
    plot_sweeps(s, ('saline',))
    
    plot_groups(d,0,'DMSO Control')
    plot_groups(d,1,'50 uM 2-APB')
    plot_groups(d,2,'200 uM 2-APB')
    plot_channels(d,0,title='Cells')
    plot_channels(d,1,title='Control')
    
    z_cell_ctrl, z_cell_2apb = six_measurement_extraction(d,s)
    f = d.sweeps[0]['F']
    
    fig, ax = plt.subplots()
    ax.plot(f/1000, np.abs(z_cell_ctrl)/1000, label='control')
    ax.plot(f/1000, np.abs(z_cell_2apb)/1000, label='50 uM 2APB')
    f2, a2 = plt.subplots()
    a2.plot(f/1000, np.unwrap(np.angle(z_cell_ctrl)), label='control')
    a2.plot(f/1000, np.unwrap(np.angle(z_cell_2apb)), label='50 uM 2APB')
    
    ax.legend()
    a2.legend()
    ax.set_ylabel(r'|Z| (k$\Omega$)')
    a2.set_ylabel(r'$\angle$Z (rad)')
    ax.set_xlabel('Frequency (kHz)')
    a2.set_xlabel('Frequency (kHz)')