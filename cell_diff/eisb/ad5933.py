# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 11:19:02 2019

@author: joeld
"""
import time, datetime
import warnings

import board, busio
from adafruit_bus_device import i2c_device
import threading
import sys


def to_byte_list(integer, n=2):
    return list(int(integer).to_bytes(n, byteorder='big'))
    
def twos_comp(x, bits=16):
    if (x & (1 << (bits - 1))) != 0: # if sign bit is set
        x = x - (1 << bits)          # negate                    
    return x

class ad5933():
    '''
    interface to AD5933 impedance converter IC
    '''
    ADDR = 0x0d # "default" I2C address of the AD5933 is fixed at 0x0d
    
    # register map for the AD5933
    _REG2_CONTROL = 0x80
    _REG3_START_FREQ = 0x82
    _REG3_INCR_FREQ = 0x85
    _REG2_NUM_INCR = 0x88
    _REG2_SETTLE_CYCLES = 0x8a
    _REG1_STATUS = 0x8f
    _REG2_TEMP = 0x92
    _REG2_REAL = 0x94
    _REG2_IMAG = 0x96
    
    OP_MODES = {  # D15-D12 codes for control register
              'No operation': 0b0000, #also 1000,1100,1101
              'Initialize':   0b0001,
              'Start':        0b0010,
              'Increment':    0b0011,
              'Repeat':       0b0100,
              'Temperature':  0b1001,
              'Power-down':   0b1010,
              'Standby':      0b1011,
              }
    OUTPUT_RANGES = {
                     '200 mVpp':4,
                     '400 mVpp':3,
                     '1 Vpp':2,
                     '2 Vpp':1,
                     }
    __version__ = '2.01'
    
    
    
    def __init__(self, output_range='200 mVpp', pga_gain=1, mode='Standby',
                 external_clock=True, reset=False, start_freq=10e3,
                 freq_step=500, num_steps=100, settle_cycles=100, mclk=16e6):
        
        # Clock frequency is 16e6 internally or can be set externally to
        # improve operation at low frequencies
        self.clock_freq = mclk
        
        # connect through I2C
        i2c = busio.I2C(board.SCL, board.SDA)
        self.i2c = i2c_device.I2CDevice(i2c, self.ADDR)
        self._buffer = bytearray(2) #used for I2C read/write   
        
        # class attributes reflect all of the writable registers in the AD5933
        self.output_range = output_range
        self.pga_gain = pga_gain
        self.external_clock = external_clock
        self.mode = mode
        self.reset = reset
        self.start_freq = start_freq # in Hz
        self.freq_step = freq_step # in Hz
        self.num_steps = num_steps
        self.settle_cycles = settle_cycles
        
        self.curr_f = 0
        self.curr_r = 0
        self.curr_i = 0

        self.thread_bool = False
        self.frequency_sweep_thread = threading.Thread(target=self.frequency_sweep, args=())
        
        
        # In addition, the AD5933 has readable registers for status, 
        # temperature, and data, which are accessed through class methods.
        
    
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.deinit()
        
    def deinit(self):
        self.i2c.i2c.deinit()
        
    @property
    def output_range(self):
        return self.__output_range
    @output_range.setter
    def output_range(self, output_range):
        if output_range not in self.OUTPUT_RANGES:
            warnings.warn('Non-valid output range setting. Valid output \
                          ranges are: "200 mVpp" "400 mVpp" "1Vpp" and "2 Vpp"\
                          . Defaulting to "400 mVpp"')
            self.__output_range = 3
        else:
            self.__output_range = self.OUTPUT_RANGES[output_range]
        self._write_output_range()
    
    @property 
    def pga_gain(self):
        return self.__pga_gain
    @pga_gain.setter
    def pga_gain(self, pga_gain):
        if pga_gain in (1,5):
            self.__pga_gain = pga_gain
        else:
            warnings.warn('pga_gain setting must be 1 or 5. Defaulting to 1.')
            self.__pga_gain = 1
        self._write_pga()
    
    @property
    def mode(self):
        return self.__mode
    @mode.setter
    def mode(self, mode):
        if mode in self.OP_MODES:
            self.__mode = mode
        else:
            self.mode = 'Standby'
            warnings.warn('Invalid mode. Defaulting to "Standby" mode.')
        self._write_mode()
    
    @property
    def num_steps(self):
        return self.__num_steps
    @num_steps.setter
    def num_steps(self, num):
        if num < 512:
            self.__num_steps = num
        else:
            self.__num_steps = 511
            warnings.warn('Number of frequency steps must not exceed 511.')
        self._write_num_increments()
        
    @property
    def start_freq(self):
        return self.__start_freq
    @start_freq.setter
    def start_freq(self,num):
        if num > 0.1 and num < 100000:
            self.__start_freq = num
        else:
            self.__start_freq = 1000
            warnings.warn('Invalid start frequency. Defaulting to 1000 Hz.')
        self._write_start_freq()
    
    @property
    def freq_step(self):
        return self.__freq_step
    @freq_step.setter
    def freq_step(self,num):
        self.__freq_step = num
        self._write_incr_freq()
    
    @property
    def settle_cycles(self):
        return self.__settle_cycles
    @settle_cycles.setter
    def settle_cycles(self,num):
        if num > 2044:
            warnings.warn('Number of settling cycles must be less than 2044. \
                          Using 2044 cycles.')
        elif num > 511 and num%2 == 1:
            warnings.warn(str(num)+' is an invalid number of settling cycles. \
                          Using '+str(num-1)+'.')
            self.__settle_cycles = num-1
        else:
            self.__settle_cycles = num
        self._write_settling_intervals()
        
    @property
    def external_clock(self):
        return self.__external_clock
    @external_clock.setter
    def external_clock(self, b):
        self.__external_clock = bool(b)
        self._write_external_clock()
        
    @property
    def reset(self):
        return self.__reset
    @reset.setter
    def reset(self, b):
        self.__reset = bool(b)
        self._write_reset()
        
    def _write_mode(self): # D12-D15
        '''Shortcut to change only the mode in the control register.'''
        code = self.OP_MODES[self.mode]
        current = self.read_register(self._REG2_CONTROL) # read only 0x80
        new = code*0b10000 + (current & 0b00001111) # keep 4 LSBs the same
        self.write_register(self._REG2_CONTROL, [new])
        
    def _write_pga(self):
        pga_bit = 1 if self.pga_gain == 1 else 0 # D8: x1 -> 1, x5 -> 0
        current = self.read_register(self._REG2_CONTROL) # read only 0x80
        new = pga_bit + (current & 0b11111110)
        self.write_register(self._REG2_CONTROL, [new])
        
    def _write_reset(self):
        rst_bit = int(self.reset) # D4
        current = self.read_register(self._REG2_CONTROL, 2)
        new = rst_bit*0b0000000000010000 + (current & 0b1111111111101111)
        self.write_register(self._REG2_CONTROL, to_byte_list(new))

    def _write_external_clock(self): # D3
        clk_bit = int(self.external_clock) # D3: external -> 1, internal -> 0
        current = self.read_register(self._REG2_CONTROL, 2)
        new = clk_bit*0b0000000000001000 + (current & 0b1111111111110111)
        self.write_register(self._REG2_CONTROL, to_byte_list(new))
        
    def _write_output_range(self): # D9-D10
        src_range = {       # D10-D9
                    1:0b00, # 2 Vpp
                    4:0b01, # 200 mVpp
                    3:0b10, # 400 mVpp
                    2:0b11, # 1 Vpp
                    }
        current = self.read_register(self._REG2_CONTROL) # read only 0x80
        new = src_range[self.output_range]*0b10+(current & 0b11111001)
        self.write_register(self._REG2_CONTROL, [new])
        
    # def write_control_reg(self):
    #     '''
    #     see AD5933 data sheet pp23-24 for complete details
    #     '''
    #     pga_bit = 1 if self.pga_gain == 1 else 0 # D8: x1 -> 1, x5 -> 0
        
    #     src_range = {       # D10-D9
    #                 1:0b00, # 2 Vpp
    #                 4:0b01, # 200 mVpp
    #                 3:0b10, # 400 mVpp
    #                 2:0b11, # 1 Vpp
    #                 }
        
    #     clk_bit = int(self.external_clock) # D3: external -> 1, internal -> 0
    #     rst_bit = int(self.reset) # D4
        
    #     reg80 = self.OP_MODES[self.mode]*0b10000 \
    #             + src_range[self.output_range]*0b10 \
    #             + pga_bit
    #     reg81 = rst_bit*0b10000 + clk_bit*0b1000
        
    #     self.write_register(self._REG2_CONTROL, [reg80, reg81])
    
    # def write_sweep_params(self):
    #     '''
    #     write_sweep_params(mclk=16e6)
        
    #     Encodes and writes the start_freq, freq_step, and num_steps attributes 
    #     into the AD5933 chip's registers
        
    #     Parameters
    #     ----------
    #     mclk : float, optional
    #         master clock frequency in Hz, default is 16e6
    #     '''
    #     mclk = self.clock_freq
        
    #     start_code = to_byte_list((4*self.start_freq/mclk)*2**27,n=3)
    #     incr_code  = to_byte_list((4*self.freq_step/mclk)*2**27,n=3)
    #     num_code   = to_byte_list(self.num_steps)
        
        
    #     self.write_register(self._REG3_START_FREQ, start_code)
    #     self.write_register(self._REG3_INCR_FREQ, incr_code)
    #     self.write_register(self._REG2_NUM_INCR, num_code)
    
    def _write_start_freq(self):
        '''
        write starting frequency to register
        '''
        mclk = self.clock_freq
        start_code = to_byte_list((4*self.start_freq/mclk)*2**27,n=3)
        self.write_register(self._REG3_START_FREQ, start_code)
    
    def _write_incr_freq(self):
        '''
        write frequency step to register
        '''
        mclk = self.clock_freq
        incr_code  = to_byte_list((4*self.freq_step/mclk)*2**27,n=3)
        self.write_register(self._REG3_INCR_FREQ, incr_code)
    
    def _write_num_increments(self):
        '''
        write the number of frequency increments to register
        '''
        num_code   = to_byte_list(self.num_steps)
        self.write_register(self._REG2_NUM_INCR, num_code)
    
    def _write_settling_intervals(self):
        # Number of settling cycles is set by a combination of a 9-bit number 
        # and a multiplication factor of 1, 2, or 4 (encoded in 2 bits).
        # Why this isn't just an 11-bit number is a mystery...
        
        # determine multiplier
        x2 = 511 < self.settle_cycles and self.settle_cycles <= 1022
        x4 = self.settle_cycles > 1022
        
        # set multiplier code
        multiplier = 0b11 if x4 else 0b01 if x2 else 0b00
        
        # calculate number to write to D8-D0
        number = self.settle_cycles
        number = number//2 if x2 else number//4 if x4 else number
        
        reg8a = multiplier*0b10 + number//0b100000000
        reg8b = number % 0b100000000
 
        self.write_register(self._REG2_SETTLE_CYCLES, [reg8a, reg8b])
        
    def read_status(self):
        '''read status register'''
        return self.read_register(self._REG1_STATUS)
        
    def read_register(self, reg, bytes_to_read=1):
        ''' block reading doesn't seem to work properly, so all read/writes
        operate 1 byte at a time'''
        # buffer = bytearray(bytes_to_read+1) # for efficiency class could have a single buffer (with fixed size) instead
        # with self.i2c as dev:
        #     buffer[0] = reg
        #     dev.write_then_readinto(buffer, buffer, out_end=1, in_start=1, 
        #                             in_end=bytes_to_read+1)
        #     return int.from_bytes(buffer[1:], 'big')
        # buffer = bytearray(bytes_to_read+1) # for efficiency class could have a single buffer (with fixed size) instead
        result=0
        with self.i2c as dev:
            for i in range(bytes_to_read):
                self._buffer[0] = reg+i
                dev.write_then_readinto(self._buffer, self._buffer, out_end=1, in_start=1, 
                                        in_end=2)
                result += self._buffer[1] * 2**i
        return result
        
    def write_register(self, reg, val_array):
        '''block writing doesn't seem to work properly, so all read/writes
        operate 1 byte at a time'''
        with self.i2c as dev:
            for i, val in enumerate(val_array):
                self._buffer[0] = reg+i
                self._buffer[1] = val & 0xff # limit val to 256 to prevent ValueErrors
                dev.write(self._buffer)
            
    def data_ready(self):
        ''' 
        D1 of the status register encodes the status of a frequency point 
        impedance measurement. The bit is set when the AD5933 has completed the
        current frequency point impedance measurement, which indicates that
        there is valid real data and imaginary data available.'''
        code = self.read_status()
        return bool(0b00000010 & code)
    
    def sweep_complete(self):
        '''
        D2 of the status register indicates the status of the programmed 
        frequency sweep. The bit is set when all programmed increments to the 
        number of increments register are complete.
        '''
        code = self.read_status()
        return bool(0b00000100 & code)
    
    def temperature_ready(self):
        return bool(self.read_status() & 0b1)
    
    def get_temperature(self):
        '''see data sheet for decode...'''
        #TODO this is value needs to be decoded
        return self.read_register(self._REG2_TEMP,2)
    
    def get_data(self):
        '''data stored in read only 16-bit two's complement'''
        
        real = self.read_register(self._REG2_REAL, 2)
        imag = self.read_register(self._REG2_IMAG, 2)
        
        self.curr_r = twos_comp(real)
        self.curr_i = twos_comp(imag)
        
        return [twos_comp(real), twos_comp(imag)]
    
    def start_thread(self):
        # self.frequency_sweep_thread.join()
        self.thread_bool == True
        self.frequency_sweep_thread = threading.Thread(target=self.frequency_sweep, args=())
        self.frequency_sweep_thread.start()
    
    def frequency_sweep(self, repeat=5, delay=0, verbose=True,
                        freq_reporting_factor=None):
        # Place the AD5933 into standby mode
        self.mode = 'Standby'
        # Program initialize with start frequency command to the control register
        self.mode = 'Initialize'
        if verbose: print('Initializing...')
        # After sufficient amount of settling time, program start frequency 
        # sweep command in the control register
        time.sleep(1)
        if verbose: print('Beginning Sweep...')
        self.mode = 'Start'
        # main loop
        data = []
        n = 1 # repeat counter
        f = self.start_freq
        timestamp = datetime.datetime.now()
        
        while self.thread_bool:
            if delay != 0:
                time.sleep(delay)
            # Poll status register to check if DFT conversion is complete
            while not self.data_ready() and self.thread_bool:
                time.sleep(0.05)
            # Read values from real and imaginary data register
            # if verbose: print('Frequency: {}'.format(f))
            t = (datetime.datetime.now() - timestamp).total_seconds()
            self.curr_t = t

            if freq_reporting_factor is None:
                data.append([t,f]+self.get_data()) # alternately could write to file here
                self.curr_f = f
            else: #used if clock division is active
                data.append([t,f/freq_reporting_factor]+self.get_data())
                self.curr_f = f/freq_reporting_factor                
            
            print(f"{self.curr_t}, {self.curr_f}, {self.curr_r}, {self.curr_i}")
            
            # Program the increment or repeat frequency command to the
            # control register
            if n < repeat:
                self.mode = 'Repeat'
                n += 1
            else:
                # Poll status register to check if frequency sweep is 
                # complete (or end sweep in single frequency mode
                if self.sweep_complete() or self.num_steps == 0 or self.thread_bool == False:
                    break
                # Otherwise increment frequency
                self.mode = 'Increment'
                n = 1
                f += self.freq_step
        
        self.should_restart_sweep()
                        
        # Program the AD5933 into power-down mode
        # self.mode = 'Power-down'
        # if verbose: print('Sweep complete.')
        # return data
        
    def should_restart_sweep(self):
        if self.thread_bool:
            self.start_thread()
        else:
            return
    
    def write_data_to_file(self, data, filename):
        var_list = [self.output_range, self.pga_gain, self.external_clock, 
            self.settle_cycles, self.__version__, str(datetime.datetime.now())]
        metadata = ('output range: {}, pga_gain: {}, external_clock: {}, '
        'settle_cycles: {}, code version: {}, timestamp: {}').format(*var_list)
        with open(filename,'w') as f:
            f.write(metadata)
            f.write('\n\n')
            f.write('T,F,R,I\n')            
            for d in data:
                line = ','.join(['{}'.format(x) for x in d]) + '\n'
                f.write(line)
                
    def single_frequency_mode(self, freq):
        '''
        single_frequency_mode(freq)
        
        Convenience method to setup the AD5933 to operate at a single frequency
        
        Parameters
        ----------
        freq : float
            frequency in Hz at which to acquire data
        '''
        self.start_freq = freq
        self.num_steps = 0
        
    def shutdown(self):
        raise SystemExit