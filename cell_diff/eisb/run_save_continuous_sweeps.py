#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 12 11:33:03 2019

@author: hannahshafferman
"""

import sys
import argparse, datetime
import os.path
from eis_board import eis_board

def main(argv):
    '''
    run_save_continuous_sweeps.py - runs a test for save_continuous_sweeps function
    takes command line args, name, dest
    
    name - str, name of the file to be saved in the format...
        name_dat_<CHANNEL NUMBER>.txt
        
    dest - str, file directory where the data file is to be saved
    
    '''
    name = sys.argv[1]
    dest = sys.argv[2]
    eisb = eis_board()
    eisb.rpi.disable_ground_isolation()
    eisb.rpi.disable_calibration()
    eisb.save_continuous_sweeps(name, dest)

def main2():
    '''TODO program sweep parameters too!'''
    desc = 'Execute sweeps on the EIS board.'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('name', type=str, help='experiment name')
    parser.add_argument('-d','--dest', type=str, 
                        help='destination directory for save files')
    parser.add_argument('-c','--cal', action='store_true',
                        help='enable calibration mode')
    parser.add_argument('-g','--gnd_iso', action='store_true',
                        help='enable ground isolation mode')
    parser.add_argument('-m','--max_cycles', type=int,
                        help='maximum number of sweeps to run')
    parser.add_argument('-T','--period', type=float,
                        help='sampling period in seconds')
    parser.add_argument('-r','--repeat', type=str,
                        help='number measurements per frequency')
    
    #TODO unfinished! (pop prog name and file name i.e. non keywords)
    kwargs = {k:v for k,v in vars(parser.parse_args(sys.argv)).iter_items() if v is not None}
    run_eisb(**kwargs)  
    

def main3(argv):
    name = sys.argv[1]
    dest = sys.argv[2]
    test_type = argv[3]
    if not test_type in ('cal','saline','test'):
        raise TypeError('select "cal" "saline" or "test" mode')
    cal = (test_type == 'cal')
    gnd_iso = not (test_type == 'saline') # cal will have ground_iso on
    # first sweep will be invalid!
    cycles = 13 if test_type == 'test' else 3
    period = 300.0 if test_type == 'test' else 60.0
    run_eisb(name, dest, calibration=cal, gnd_iso=gnd_iso, cycles=cycles, 
             period=period)
    
def program_sweeps(eisb, start=10e3, step=1000, steps=90):
    for ch in range(2):
        eisb.channel(ch)
        ad = eisb.ad(ch)
        ad.start_freq=start
        ad.freq_step = step
        ad.num_steps = steps
        ad.write_sweep_params()
        
def run_eisb(name, dest='', calibration=False, gnd_iso=True, cycles=None, 
             period=300.0, repeat=5):
    eisb = eis_board()
    program_sweeps(eisb)
    if calibration:
        eisb.rpi.enable_calibration()
    else:
        eisb.rpi.disable_calibration()
    if gnd_iso:
        eisb.rpi.enable_ground_isolation()
    else:
        eisb.rpi.disable_ground_isolation()
        
    with open(os.path.join(dest,name+'_test.txt'), 'w') as f:
        f.write('date={},calibration={},ground_isolation={},period={}'.format(
                str(datetime.datetime.now()),calibration,gnd_iso,period,))
        
    eisb.save_continuous_sweeps(name, dest, repeat=5, Ts=period, 
                                num_sweeps=cycles)
    eisb.close()
    

if __name__ == '__main__':
    main3(sys.argv)
#    parser = main2()
#    print(parser.print_help())
#    
#    print(parser.parse_args('foo -g -d data -T 30'.split()))