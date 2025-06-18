# -*- coding: utf-8 -*-
"""
Created on Wed Apr 17 18:59:59 2019

@author: jdunga01
"""
import time
import os.path
import numpy as np

from ad5933 import ad5933
from pi_gpio import pi_gpio
# from tca9543a import tca9543a
from thread_timing import timed_execution
       
__version__ = '2.00'

class eis_board():
    '''
    updated for board V3.2 (single channel, 4pt measurement)
    '''
    NUM_CH = 1 # excluding control
    CAL_CH = 0 # calibration channel number
    
    def __init__(self, gpio_kw={}, ad_kw={}):
        
        # raspberry pi control
        self.rpi = pi_gpio(**gpio_kw)
        # ad5933 impedance analyzer chip
        self.ad = ad5933(**ad_kw)
        self.ad.initialize()
       
      
    def close(self):
        self.rpi.cleanup_GPIO()
        self.ad.deinit()
        
    def channel(self, ch):
        pass
        
    def single_frequency(self, ch, freq, repeat=5, delay=500):
        '''
        single frequency measurement for a single channel
        '''
        self.ad.single_frequency_mode(freq)
        return self.ad.frequency_sweep(repeat, delay)
    
    def save_single_frequency_to_file(self, name, *args, **kwargs):
        '''
        TODO: documentation
        '''
        datas = self.alternating_single_frequency(*args, **kwargs)
        for ch in range(self.NUM_CH-1):
            self.ad.write_data_to_file(datas[ch],'{}_dat_{}.txt'.format(name,ch))

    def save_continuous_sweeps(self, name, dest='', repeat=5, Ts=300.0, ch=[],
                               num_sweeps=None, sweep_type='full_range'):
        '''
        Saves frequency sweep data to file at given time intervals.
        
        Will save two (one for each channel) sweep files. Timing for sampling
        period is handled in a separate thread so that the sample time doesn't
        drift because of the sweep execution time. Sweep parameters must be
        configured for ad5933 instances prior to running this method.
        
        Parameters
        ----------
        name : str
            The basename for the files to be saved. `name` will be appended
            with the channel number and iteration number.
        dest : str, optional
            A directory destination into which files should be saved. Defaults
            to '', meaning the current working directory.
        repeat : int, optional
            The number of times a measurement will be repeated at each
            frequency in the linear sweep (default is 5).
        Ts : 300.0, optional
            The time in seconds between the start of sweeps. This sample period
            should be significantly longer the time it takes a sweep to execute.
        ch : list of int, optional
            A list of the channels to sweep (default sweeps all channels).
        num_sweeps : int, optional
            The number of sweeps to be executed. Default is None, in which case
            the sweeps will be repeated until the user enters "q" into the 
            command line.
        sweep_type : {'alternating','independent','low_freq','full_range'}
            Enables other sweep modes (default is 'alternating').
        '''
        progress = [] # iteration number will be stored in the length of this
                      # progress list because threads need a mutable object
        name = os.path.join(dest,name)
        func_args = [name]
        func_kwargs={'ch':ch,'progress':progress,'repeat':repeat}
#        if sweep_type == 'alternating':
#            timed_execution(self.save_alternating_sweep, Ts, *func_args, 
#                            num_intervals=num_sweeps)
#        elif sweep_type == 'low_freq':
#            timed_execution(self.save_low_freq_sweep, Ts, *func_args, 
#                            num_intervals=num_sweeps)
#        elif sweep_type == 'independent':
#            timed_execution(self.save_test, Ts, *func_args, 
#                            num_intervals=num_sweeps)
        if sweep_type == 'full_range':
            timed_execution(self.save_full_range_sweep, Ts, *func_args,  
                            num_intervals=num_sweeps, **func_kwargs)
        else:
            raise ValueError("sweep_type must be one of 'alternating', "
                             "'independent', 'full_range', or 'low_freq'")

    def freq_sweep_full_range(self, ch, repeat=10, num_steps=50):
        '''
        sweep from 1k to 100k using `num_steps` log-spaced frequencies
        
        note that this method is probably very inefficient because it
        implements the sweep a series of single frequency measurements, so the
        ad5933 is initialized and powered down at every frequency.
        '''
        freqs = np.round(np.logspace(3,5,num=num_steps))
        self.channel(ch)
        ad = self.ad
        # save previous sweep params
        start_old, step_old, num_old = ad.start_freq, ad.freq_step, ad.num_steps
        # execute sweep as a series of single point measurements
        data = []
        for freq in freqs:
            if freq < 10e3:
                ad.single_frequency_mode(freq*4)
                self.rpi.set_clock_divide(4)
                self.rpi.enable_clock_divider()
                time.sleep(0.1)
                data += ad.frequency_sweep(repeat=repeat, verbose=True, 
                                         freq_reporting_factor=4)
                self.rpi.disable_clock_divider()
            else:
                ad.single_frequency_mode(freq)
                data += ad.frequency_sweep(repeat=repeat, verbose=True)
            print(data)
        
        # restore parameters
        ad.start_freq, ad.freq_step, ad.num_steps = start_old, step_old, num_old
        ad.write_sweep_params()
        return data        

    def save_full_range_sweep(self, name, ch=[], progress=[], repeat=5, num_steps=50):
        '''
        Executes a full range (1-100kHz) sweep and saves it to file.
        
        Executes a full range (1-100kHz) sweep (using `num_steps` log-spaced
        frequencies) and saves the data to file using the ad5933's 
        write_data_to_file method.
        
        Parameters
        ----------
        name : str
            A name (and directory location if desired) for the data file to be
            written to disk. The channel number and sweep iteration will be
            appended along with a .txt file extension
        progress : list, optional
            `progress` is primarily used by eis_board.save_continuous_sweeps,
            which needs a mutable object to keep track of the number of 
            completed loop iterations
        repeat : int, optional
            The number of times a measurement will be repeated at each
            frequency in the linear sweep (default is 5).
        num_steps : int, optional
            The number of (log-spaced) freqency points to acquire (default is 
            50).
        '''
        channels = ch if ch else range(self.NUM_CH)
        for chan in channels:
            data = self.freq_sweep_full_range(ch=chan, repeat=repeat, 
                                             num_steps=num_steps)
            filename = '{}_ch{}_{}.txt'.format(name,chan,len(progress))
            self.ad.write_data_to_file(data,filename)
        progress.append(True)
               
    def freq_sweep(self, ch, repeat=5):
        self.channel(ch)
        return self.ad.frequency_sweep(repeat=repeat)
        
    def save_freq_sweep(self, name, progress=[], repeat=5):
        '''
        Executes a frequency sweep (using fixed value sweep parameters) and 
        saves the data to file using the ad5933's write_data_to_file method.
        
        Parameters
        ----------
        name : str
            A name (and directory location if desired) for the data file to be
            written to disk. The channel number and sweep iteration will be
            appended along with a .txt file extension
        progress : list, optional
            `progress` is primarily used by eis_board.save_continuous_sweeps,
            which needs a mutable object to keep track of the number of 
            completed loop iterations
        repeat : int, optional
            The number of times a measurement will be repeated at each
            frequency in the linear sweep (default is 5).
        num_steps : int, optional
            The number of freqency points to acquire in each clock frequency
            subdivision (default is 10).
        '''
        for ch in range(self.NUM_CH):
            data = self.freq_sweep(ch=ch, repeat=repeat)
            filename = '{}_ch{}_{}.txt'.format(name,ch,len(progress))
            self.ad.write_data_to_file(data,filename)
        progress.append(True)



# class eis_board_old():
#     '''
#     TODO: helper methods to reprogram sweep parameters for both ad5933 chips
#     '''
    
    
#     def __init__(self, gpio_kw={}, tca_kw={}, ad0_kw={}, ad1_kw={}):
        
#         # raspberry pi control
#         self.rpi = self.init_rpi(**gpio_kw)
#         # i2c mux for two ad5933 chips        
#         self.tca = tca9543a(**tca_kw)
#         # two ad5933 impedance analyzer chips
#         self.ad0 = ad5933(**ad0_kw)
#         self.ad1 = ad5933(**ad1_kw)
        
#         self.tca.set_channels(True,False)
#         self.ad0.initialize()
        
#         self.tca.set_channels(False,True)
#         self.ad1.initialize()
        
#     def init_rpi(self, **kw):
#         return pi_gpio(**kw)
    
#     def channel0(self):
#         self.tca.set_channels(True,False)
#     def channel1(self):
#         self.tca.set_channels(False,True)
#     def channel(self,ch):
#         if ch is 0:
#             self.tca.set_channels(True,False)
#         elif ch is 1:
#             self.tca.set_channels(False,True)
#         else:
#             self.tca.set_channels(False,False)
            
#     def ad(self, ch):
#         '''
#         Helper method to access ad5933 instances.
        
#         Parameters
#         ----------
#         ch : {0,1}
        
#         Returns
#         -------
#         reference to this eis_boards's ad5933 instance
#         '''
#         if ch is 0:
#             return self.ad0
#         elif ch is 1:
#             return self.ad1
#         else:
#             raise ValueError('Channel must be 0 or 1.')
        
#     def close(self):
#         self.rpi.cleanup_GPIO()
      
#     def save_alternating_sweep(self, name, progress=[], repeat=5):
#         '''
#         Executes an alternating sweep and saves it to file.
        
#         Executes an alternating sweep (using the currently configured ad5933
#         sweep parameters) and saves the data to file using the ad5933's 
#         write_data_to_file method.
        
#         Parameters
#         ----------
#         name : str
#             A name (and directory location if desired) for the data file to be
#             written to disk. The channel number and sweep iteration will be
#             appended along with a .txt file extension
#         progress : list, optional
#             `progress` is primarily used by eis_board.save_continuous_sweeps,
#             which needs a mutable object to keep track of the number of 
#             completed loop iterations
#         repeat : int, optional
#             The number of times a measurement will be repeated at each
#             frequency in the linear sweep (default is 5).
#         '''
#         datas = self.alternating_sweep(repeat=repeat)
#         for ch in range(2):
#             filename = '{}_ch{}_{}.txt'.format(name,ch,len(progress))
#             self.ad(ch).write_data_to_file(datas[ch],filename)
#         progress.append(True)
        
#     def save_single_frequency():
#         '''
#         TODO: implement analog to save_alternating sweep for a single frequency
#         measurement (through it should append to file or a memory object)
#         '''
#         raise NotImplementedError()
    
#     def save_single_frequency_to_file(self, name, *args, **kwargs):
#         '''
#         TODO: documentation
#         '''
#         datas = self.alternating_single_frequency(*args, **kwargs)
#         for ch in range(2):
#             self.ad(ch).write_data_to_file(datas[ch],'{}_dat_{}.txt'.format(name,ch))
        
#     def single_frequency(self, ch, freq, repeat=5, delay=500):
#         '''
#         single frequency measurement for a single channel
#         '''
#         self.channel(ch)
#         self.ad(ch).single_frequency_mode(freq)
#         return self.ad(ch).frequency_sweep(repeat, delay)
    
#     def save_single_frequency_calibration(self, name, freq, **kwargs):
#         self.rpi.enable_calibration()
#         for ch in range(2):
#             data = self.single_frequency(ch, freq, **kwargs)
#             filename = '{}_{}Hz_cal_ch{}.txt'.format(name,freq,ch)
#             self.ad(ch).write_data_to_file(data, filename)
            
#     def save_single_frequency_test(self, name, freq, **kwargs):
#         self.rpi.disable_calibration()
#         self.rpi.enable_ground_isolation()
#         for ch in range(2):
#             data = self.single_frequency(ch, freq, **kwargs)
#             filename = '{}_{}Hz_dat_ch{}.txt'.format(name,freq,ch)
#             self.ad(ch).write_data_to_file(data, filename)
    
#     def save_continuous_sweeps(self, name, dest='', repeat=5, Ts=300.0, 
#                                num_sweeps=None, sweep_type='alternating'):
#         '''
#         Saves frequency sweep data to file at given time intervals.
        
#         Will save two (one for each channel) sweep files. Timing for sampling
#         period is handled in a separate thread so that the sample time doesn't
#         drift because of the sweep execution time. Sweep parameters must be
#         configured for ad5933 instances prior to running this method.
        
#         Parameters
#         ----------
#         name : str
#             The basename for the files to be saved. `name` will be appended
#             with the channel number and iteration number.
#         dest : str, optional
#             A directory destination into which files should be saved. Defaults
#             to '', meaning the current working directory.
#         repeat : int, optional
#             The number of times a measurement will be repeated at each
#             frequency in the linear sweep (default is 5).
#         Ts : 300.0, optional
#             The time in seconds between the start of sweeps. This sample period
#             should be significantly longer the time it takes a sweep to execute.
#         num_sweeps : int, optional
#             The number of sweeps to be executed. Default is None, in which case
#             the sweeps will be repeated until the user enters "q" into the 
#             command line.
#         sweep_type : {'alternating','independent','low_freq','full_range'}
#             Enables other sweep modes (default is 'alternating').
#         '''
#         progress = [] # iteration number will be stored in the length of this
#                       # progress list because threads need a mutable object
#         name = os.path.join(dest,name)
#         func_args=[name,progress,repeat]
#         if sweep_type == 'alternating':
#             timed_execution(self.save_alternating_sweep, Ts, *func_args, 
#                             num_intervals=num_sweeps)
#         elif sweep_type == 'low_freq':
#             timed_execution(self.save_low_freq_sweep, Ts, *func_args, 
#                             num_intervals=num_sweeps)
#         elif sweep_type == 'independent':
#             timed_execution(self.save_test, Ts, *func_args, 
#                             num_intervals=num_sweeps)
#         elif sweep_type == 'full_range':
#             timed_execution(self.save_full_range_sweep, Ts, *func_args, 
#                             num_intervals=num_sweeps)
#         else:
#             raise ValueError("sweep_type must be one of 'alternating', "
#                              "'independent', 'full_range', or 'low_freq'")
    
    
#     def alternating_sweep(self, repeat=5):
#         '''
#         Runs a simultaneous sweep on both AD5933 chips.
        
#         Sweeps will used previously programmed ad5933 sweep parameters. Note
#         that execution of this function can take a significant amount of time
#         (usually ~30s).
        
#         Parameters
#         ----------
#         repeat : int, optional
#             The number of times a measurement will be repeated at each
#             frequency in the linear sweep (default is 5).
        
#         Returns
#         -------
#         array_like, array_like
#             two data sets containing the sweep data from each channel
#         '''
#         self.channel0()
#         # Place the AD5933 into standby mode
#         self.ad0.set_and_write_mode('Standby')
#         # Program initialize with start frequency command to the control register
#         self.ad0.set_and_write_mode('Initialize')
#         print('Initializing channel 1')
#         self.channel1()
#         self.ad1.set_and_write_mode('Standby')
#         self.ad1.set_and_write_mode('Initialize')
#         print('Initializing channel 2')
#         # After sufficient amount of settling time, program start frequency 
#         # sweep command in the control register
#         time.sleep(5)
#         print('Beginning Sweeps...')
#         self.channel0()
#         self.ad0.set_and_write_mode('Start')
#         self.channel1()
#         self.ad1.set_and_write_mode('Start')
#         # main loop
#         datas = [[],[]]
#         n = 1 # repeat counter
#         i = 0 # loop counter
#         #TODO add check that sweeps are identical
#         start, step = self.ad0.start_freq, self.ad0.freq_step
#         f = start
#         timestamp = datetime.datetime.now()
#         while True:
#             ch = i%2
#             ad = self.ad(ch)
#             self.channel(ch)
#             # Poll status register to check if DFT conversion is complete
#             while not ad.data_ready():
#                 time.sleep(0.05)
#             # Read values from real and imaginary data register
#             print('Channel {} Frequency: {}'.format(ch,f))
#             t = (datetime.datetime.now() - timestamp).total_seconds()
#             datas[ch].append([t,f]+ad.get_data()) # alternately could write to file here
#             # Poll status register to check if frequency sweep is complete
#             if ad.sweep_complete() and ch==1:
#                 break
#             else:
#                 # Program the increment or repeat frequency command to the
#                 # control register
#                 if n <= repeat:
#                     ad.set_and_write_mode('Repeat')
#                     n += 1
#                 else:
#                     ad.set_and_write_mode('Increment')
#                     n = 1
#                     i += 1
#                     if ch==1:
#                         f += step
#         # Program the AD5933 into power-down mode
#         for i in range(2):
#             self.channel(i)
#             self.ad(i).set_and_write_mode('Power-down')
#         return datas[0],datas[1]        

#     def alternating_single_frequency(self, freq=None, repeat=100, Ts=1.0):
#         '''
#         Acquires a fixed number of data points continuously from both channels
        
#         Parameters
#         ----------
#         freq : float, optional
#             frequency at which to poll data, default is None which reads the 
#             value currently set in channel 0 AD5933 start frequency register
#         repeat : int, optional
#             number of data points to acquire (on each channel), default is 100
#         Ts : float
#             sampling period in seconds, default is 1.0
            
#         Returns
#         ----------
#         d1, d2: array_like
#             array of data point lists of the form [timestamp, frequency, real, 
#             imag]
#         '''
#         self.channel0()
#         self.ad0.single_frequency_mode(self.ad0.start_freq if freq is None else freq)
#         # Place the AD5933 into standby mode
#         self.ad0.set_and_write_mode('Standby')
#         # Program initialize with start frequency command to the control register
#         self.ad0.set_and_write_mode('Initialize')
#         print('Initializing channel 1')
#         # repeat for channel 1
#         self.channel1()
#         self.ad1.single_frequency_mode(self.ad0.start_freq if freq is None else freq)
#         self.ad1.set_and_write_mode('Standby')
#         self.ad1.set_and_write_mode('Initialize')
#         print('Initializing channel 2')
#         # After sufficient amount of settling time, program start frequency 
#         # sweep command in the control register
#         time.sleep(5)
#         print('Beginning Sweeps...')
#         self.channel0()
#         self.ad0.set_and_write_mode('Start')
#         self.channel1()
#         self.ad1.set_and_write_mode('Start')
#         # main loop
#         datas = [[],[]]
#         #TODO add check that sweeps are identical
#         f = self.ad0.start_freq
#         timestamp = datetime.datetime.now()
#         for _ in range(repeat):
#             for ch in range(2):
#                 ad = self.ad(ch)
#                 self.channel(ch)
#                 # Poll status register to check if DFT conversion is complete
#                 while not ad.data_ready():
#                     time.sleep(0.05)
#                 # Read values from real and imaginary data register
#                 print('Channel {} Frequency: {}'.format(ch,f))
#                 t = (datetime.datetime.now() - timestamp).total_seconds()
#                 datas[ch].append([t,f]+ad.get_data()) # alternately could write to file here
#                 # Poll status register to check if frequency sweep is complete
#                 if ad.sweep_complete():
#                     break
#                 else:
#                     # Program the increment or repeat frequency command to the
#                     # control register
#                     ad.set_and_write_mode('Repeat')
#             time.sleep(Ts)
            
#         # Program the AD5933 into power-down mode
#         for i in range(2):
#             self.channel(i)
#             self.ad(i).set_and_write_mode('Power-down')
#         return datas[0],datas[1]
         
    
#     def freq_sweep_low_adjusted(self, ch):
#         '''TODO: sweep through the programmed frequencies, automatically slowing 
#         the clock appropriately for low freqency data'''
#         raise NotImplementedError()
#         self.channel(ch)
#         ad = self.ad(ch)
#         # get intended frequencies
#         f = ad.start_freq+(np.arange(ad.num_steps)*ad.freq_step)
#         def find_factor(freq):
#             for lim, factor in reversed(pi_gpio.freq_limits):
#                 if freq < lim: return factor
#             return 1
#         factors = [find_factor(freq) for freq in f]
        
#         ## setup sweep
#         ad.set_and_write_mode('Standby')
#         ad.set_and_write_mode('Initialize')
#         time.sleep(5)
#         ad.set_and_write_mode('Start')
#         data = []
#         n = 1 # repeat counter
#         f = ad.start_freq
#         while True:
#             pass
        
#     def freq_sweep_full_range(self, ch, repeat=10, num_steps=50):
#         '''sweep from 1k to 100k using `num_steps` log-spaced frequencies'''
#         freqs = np.round(np.logspace(3,5,num=num_steps))
#         self.channel(ch)
#         ad = self.ad(ch)
#         # save previous sweep params
#         start_old, step_old, num_old = ad.start_freq, ad.freq_step, ad.num_steps
#         # execute sweep as a series of single point measurements
#         data = []
#         for freq in freqs:
#             if freq < 10e3:
#                 ad.single_frequency_mode(freq*4)
#                 self.rpi.set_clock_divide(4)
#                 self.rpi.enable_clock_divider()
#                 time.sleep(1)
#                 data += ad.frequency_sweep(repeat=repeat, verbose=True, 
#                                          freq_reporting_factor=4)
#                 self.rpi.disable_clock_divider()
#             else:
#                 ad.single_frequency_mode(freq)
#                 data += ad.frequency_sweep(repeat=repeat, verbose=True)
        
#         # restore parameters
#         ad.start_freq, ad.freq_step, ad.num_steps = start_old, step_old, num_old
#         ad.write_sweep_params()
#         return data        
            
#     def low_freq_sweep_fixed(self, ch, repeat=5, num_steps=10):
#         self.channel(ch)
#         ad = self.ad(ch)
#         # save previous sweep parameters first
#         start_old, step_old, num_old = ad.start_freq, ad.freq_step, ad.num_steps
#         # have to rewrite frequency registers mid sweep...
#         start_freq = 100
#         data = []
#         for freq_lim, factor in reversed(pi_gpio.freq_limits):
#             # slowing down the clock also slows the DDS, so the source
#             # frequencies need to be adjusted as well
#             ad.start_freq = start_freq*factor
#             ad.num_steps = num_steps-1 # don't double up 
#             ad.freq_step = factor*(freq_lim-start_freq)/num_steps
#             ad.write_sweep_params()
                        
#             self.rpi.set_clock_divide(factor)
#             # reduce clock speed
#             self.rpi.enable_clock_divider()
#             # perform sweep
#             time.sleep(3)
#             dat = ad.frequency_sweep(repeat=repeat, verbose=True,
#                                     freq_reporting_factor=factor)
#             # restore clock speed
#             self.rpi.disable_clock_divider()
            
#             data += dat            
#             start_freq = freq_lim

#         # restore parameters
#         ad.start_freq, ad.freq_step, ad.num_steps = start_old, step_old, num_old
#         ad.write_sweep_params()
#         return data
    
#     def save_low_freq_sweep(self, name, progress=[], repeat=5, num_steps=10):
#         '''
#         Executes a low frequency (<10kHz) sweep and saves it to file.
        
#         Executes a low frequency (<10kHz) sweep (using fixed value
#         sweep parameters) and saves the data to file using the ad5933's 
#         write_data_to_file method.
        
#         Parameters
#         ----------
#         name : str
#             A name (and directory location if desired) for the data file to be
#             written to disk. The channel number and sweep iteration will be
#             appended along with a .txt file extension
#         progress : list, optional
#             `progress` is primarily used by eis_board.save_continuous_sweeps,
#             which needs a mutable object to keep track of the number of 
#             completed loop iterations
#         repeat : int, optional
#             The number of times a measurement will be repeated at each
#             frequency in the linear sweep (default is 5).
#         num_steps : int, optional
#             The number of freqency points to acquire in each clock frequency
#             subdivision (default is 10).
#         '''
#         for ch in range(2):
#             data = self.low_freq_sweep_fixed(ch=ch, repeat=repeat, 
#                                              num_steps=num_steps)
#             filename = '{}_ch{}_{}.txt'.format(name,ch,len(progress))
#             self.ad(ch).write_data_to_file(data,filename)
#         progress.append(True)
        
#     def save_full_range_sweep(self, name, progress=[], repeat=5, num_steps=50):
#         '''
#         Executes a full range (1-100kHz) sweep and saves it to file.
        
#         Executes a full range (1-100kHz) sweep (using `num_steps` log-spaced
#         frequencies) and saves the data to file using the ad5933's 
#         write_data_to_file method.
        
#         Parameters
#         ----------
#         name : str
#             A name (and directory location if desired) for the data file to be
#             written to disk. The channel number and sweep iteration will be
#             appended along with a .txt file extension
#         progress : list, optional
#             `progress` is primarily used by eis_board.save_continuous_sweeps,
#             which needs a mutable object to keep track of the number of 
#             completed loop iterations
#         repeat : int, optional
#             The number of times a measurement will be repeated at each
#             frequency in the linear sweep (default is 5).
#         num_steps : int, optional
#             The number of (log-spaced) freqency points to acquire (default is 
#             50).
#         '''
#         for ch in range(2):
#             data = self.freq_sweep_full_range(ch=ch, repeat=repeat, 
#                                              num_steps=num_steps)
#             filename = '{}_ch{}_{}.txt'.format(name,ch,len(progress))
#             self.ad(ch).write_data_to_file(data,filename)
#         progress.append(True)
               
#     def freq_sweep(self, ch, repeat=5):
#         self.channel(ch)
#         return self.ad(ch).frequency_sweep(repeat=repeat)
        
#     def save_freq_sweep(self, name, progress=[], repeat=5):
#         '''
#         Executes a low frequency (<10kHz) sweep and saves it to file.
        
#         Executes a low frequency (<10kHz) sweep (using fixed value
#         sweep parameters) and saves the data to file using the ad5933's 
#         write_data_to_file method.
        
#         Parameters
#         ----------
#         name : str
#             A name (and directory location if desired) for the data file to be
#             written to disk. The channel number and sweep iteration will be
#             appended along with a .txt file extension
#         progress : list, optional
#             `progress` is primarily used by eis_board.save_continuous_sweeps,
#             which needs a mutable object to keep track of the number of 
#             completed loop iterations
#         repeat : int, optional
#             The number of times a measurement will be repeated at each
#             frequency in the linear sweep (default is 5).
#         num_steps : int, optional
#             The number of freqency points to acquire in each clock frequency
#             subdivision (default is 10).
#         '''
#         for ch in range(2):
#             data = self.freq_sweep(ch=ch, repeat=repeat)
#             filename = '{}_ch{}_{}.txt'.format(name,ch,len(progress))
#             self.ad(ch).write_data_to_file(data,filename)
#         progress.append(True)    
        
        
# class eis_board_v2(eis_board):
    
#     def init_rpi(self, **kw):
#         return pi_gpio_v2(**kw)
     
#     def select_control(self, ch):
#         '''
        
#         Parameters
#         ----------
#         ch : int
#             0 -> upstream control, 1 -> downstream control
#         '''
#         self.rpi.set_control(0 if ch==0 else 1) 

#     def save_freq_sweep(self, name, progress=[], repeat=5):
#         '''
#         Executes a low frequency (<10kHz) sweep and saves it to file.
        
#         Executes a low frequency (<10kHz) sweep (using fixed value
#         sweep parameters) and saves the data to file using the ad5933's 
#         write_data_to_file method.
        
#         Parameters
#         ----------
#         name : str
#             A name (and directory location if desired) for the data file to be
#             written to disk. The channel number and sweep iteration will be
#             appended along with a .txt file extension
#         progress : list, optional
#             `progress` is primarily used by eis_board.save_continuous_sweeps,
#             which needs a mutable object to keep track of the number of 
#             completed loop iterations
#         repeat : int, optional
#             The number of times a measurement will be repeated at each
#             frequency in the linear sweep (default is 5).
#         num_steps : int, optional
#             The number of freqency points to acquire in each clock frequency
#             subdivision (default is 10).
#         '''
#         for ch in range(3):
#             phys_chan = ch if ch!=2 else 0
#             if ch==0:
#                 self.select_control(0)
#             if ch==2:
#                 self.select_control(1)
#             data = self.freq_sweep(ch=phys_chan, repeat=repeat)
#             filename = '{}_ch{}_{}.txt'.format(name,ch,len(progress))
#             self.ad(phys_chan).write_data_to_file(data,filename)
#         progress.append(True) 
          
#     def save_full_range_sweep(self, name, progress=[], repeat=5, num_steps=50):
#         '''
#         Executes a full range (1-100kHz) sweep and saves it to file.
        
#         Executes a full range (1-100kHz) sweep (using `num_steps` log-spaced
#         frequencies) and saves the data to file using the ad5933's 
#         write_data_to_file method.
        
#         Parameters
#         ----------
#         name : str
#             A name (and directory location if desired) for the data file to be
#             written to disk. The channel number and sweep iteration will be
#             appended along with a .txt file extension
#         progress : list, optional
#             `progress` is primarily used by eis_board.save_continuous_sweeps,
#             which needs a mutable object to keep track of the number of 
#             completed loop iterations
#         repeat : int, optional
#             The number of times a measurement will be repeated at each
#             frequency in the linear sweep (default is 5).
#         num_steps : int, optional
#             The number of (log-spaced) freqency points to acquire (default is 
#             50).
#         '''
#         for ch in range(3):
#             phys_chan = ch if ch!=2 else 0
#             if ch==0:
#                 self.select_control(0)
#             if ch==2:
#                 self.select_control(1)
#             data = self.freq_sweep_full_range(ch=phys_chan, repeat=repeat, 
#                                              num_steps=num_steps)
#             filename = '{}_ch{}_{}.txt'.format(name,ch,len(progress))
#             self.ad(phys_chan).write_data_to_file(data,filename)
#         progress.append(True)   
             
#     def save_full_range_controls(self, name, progress=[], repeat=5, num_steps=50):
#         phys_chan=0
#         for ch in range(2):
#             self.select_control(ch)
#             data = self.freq_sweep_full_range(ch=phys_chan, repeat=repeat, 
#                                               num_steps=num_steps)
#             filename = '{}_ch{}_{}.txt'.format(name,ch,len(progress))
#             self.ad(phys_chan).write_data_to_file(data,filename)
#         progress.append(True)
 
#     def save_continuous_control_sweeps(self, name, dest='', repeat=5, Ts=300.0,
#             num_sweeps=3):
                                   
#         progress = [] # iteration number will be stored in the length of this
#                       # progress list because threads need a mutable object
#         name = os.path.join(dest,name)
#         func_args=[name,progress,repeat]
#         timed_execution(self.save_full_range_controls, Ts, *func_args,
#                         num_intervals=num_sweeps)

        
def int_to_bin(x):
        if x == 0: return [0]
        bit = []
        while x:
                bit.append(x % 2)
                x >>= 1
        return bit[::-1]        



if __name__ == '__main__':
    
    eisb = eis_board()
    eisb.channel0()
    d0 = eisb.ad0.frequency_sweep()
    eisb.ad0.write_data_to_file(d0, 'ch0.txt')
    d1 = eisb.ad1.frequency_sweep()
    eisb.ad1.write_data_to_file(d1, 'ch1.txt')
