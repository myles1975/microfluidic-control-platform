# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 11:26:16 2019

@author: joeld
"""
import board, digitalio


def digit_to_4bit(d):
    ''' digits to list of 4 boolean - LSB first!'''
    bits = []
    for _ in range(4):
            bits.append(d%2)
            d >>= 1
    return bits

def calc_clock_divide(N, mode=2):
    '''See documentation for CD74HC4059'''
    d = N//mode
    if d>99 or N%mode!=0 or N<3: 
            raise ValueError(
                'N is too large, too small, or not divisible by mode.')
    
    d0 = digit_to_4bit(d%10)
    d1 = digit_to_4bit(d//10)
    return d0,d1 

def clock_divide_N(freq):
    for f,n in reversed(pi_gpio.freq_limits):
        if freq < f: return n
    else: return 1
    
def config_output_pin(assignment):
    pin = digitalio.DigitalInOut(assignment)
    pin.direction = digitalio.Direction.OUTPUT
    pin.drive_mode = digitalio.DriveMode.PUSH_PULL
    pin.value = False
    return pin

class pi_gpio():
    '''
    wrapper for Rasberry Pi 3B+ GPIO interactions with all digital logic 
    components on the EIS board (v3.2)
    '''
    CLK_DIV = board.D7

    CLK_PINS = ((5, board.D5),
                (6, board.D6),
                (7, board.D12),
                (8, board.D13),
                (9, board.D19),
                (10,board.D16),
                (11,board.D26),
                (12,board.D20))
    
    # AD5933 is inaccurate at low frequencies - see UG-364
    # [(low_limit, clock_div),...]
    freq_limits = [(10e3,4),(5e3,4),(1e3,8),(300,16),(200,32)]
    

    def __init__(self, **kwargs):
        self.j_clk = {} # holds the pins controlling the frequency divider
        self.setup_GPIO()
    
    def setup_GPIO(self):
        '''configure GPIO pins and set default values'''
        for i,assignment in self.CLK_PINS:
            self.j_clk[i] = config_output_pin(assignment)
        self.clk_div = config_output_pin(self.CLK_DIV)

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup_GPIO()

    def cleanup_GPIO(self):
        for pin in self.j_clk.values():
            pin.deinit()
        self.clk_div.deinit()

    def set_clock_divide(self, N, mode=2):
        '''
        For board v3.2:
        Mode is set by jumpers on the board (J1-J3) these determine KA-KC.
        KA-KC are tied to Vdd, so the mode is fixed at 2. 
        '''
        d0,d1 = calc_clock_divide(N,mode)        
        for i,b in enumerate(d0):
                self.j_clk[i+9].value = b
        for i,b in enumerate(d1):
                self.j_clk[i+5].value =  b
    
    def enable_clock_divider(self):
        self.clk_div.value = True
    def disable_clock_divider(self):
        self.clk_div.value = False
    

