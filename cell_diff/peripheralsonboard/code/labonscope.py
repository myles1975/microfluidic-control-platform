import time, warnings
import board
import busio
import digitalio
from simple_pid import PID
import threading

from utils import InterruptThread
from adafruit_mcp230xx.mcp23017 import MCP23017
import adafruit_mcp9600
import sys

def thermocouple_connect(i2c, address=0x60):
    # defaults to "K" type thermocouple type
    return adafruit_mcp9600.MCP9600(i2c, address=address)

def i2c_connect(freq=10000):
    # establish an I2C connection, reduce speed for reliability
    return busio.I2C(board.SCL, board.SDA, frequency=freq)
    
def mcp_connect(i2c, address= 0):
    #connect to MCP23018, 0x20 is the default address when address pin is grounded
    mcp = MCP23017(i2c, address=address)
    
    #set all gpio to output (equivalent to pin.direction=digitalio.Direction.OUTPUT on all pins)
    mcp.iodir = 0 
    #set all pins to pull up configuration (equivalent to pin.pull=digitalio.Pull.UP on all pins)
    mcp.gppu = 0xffff 

    return mcp

class LoS():
    '''board v2.0 05/2023
    
    note: heat pin (D27) is configured as a digital pin rather than PWM
    '''
    NUM_VALVES = 8
    EN_PINS = (1,3,5,7,9,11,13,15)
    ST_PINS = (0,2,4,6,8,10,12,14)
    PULSE_TIME = 0.05 # seconds, max activation time of LHL valves is 30ms
    
    # in board v2.0 these valve indices are wired incorrectly
    BROKEN_VALVES = (1,2,4,6)
    
    
    def __init__(self, i2c_freq=100000, mcp_addr=0x20, tc_addr=0x60):
        self.i2c = i2c_connect(freq=i2c_freq)
        self.mcp = mcp_connect(self.i2c, address=mcp_addr) 
        self.init_valves()
        self.tc = thermocouple_connect(self.i2c, address=tc_addr)
        self.heat = self.init_heat()
        self.heater_thread = None
        self.pid_thread = None
        self.run_thread = False
        
    def init_heat(self):
        heat_pin = digitalio.DigitalInOut(board.D27)
        heat_pin.direction = digitalio.Direction.OUTPUT
        heat_pin.drive_mode = digitalio.DriveMode.PUSH_PULL 
        heat_pin.value = False
        return heat_pin
        
        
    def init_valves(self):
        self.ens = [self.mcp.get_pin(i) for i in self.EN_PINS]
        self.sts = [self.mcp.get_pin(i) for i in self.ST_PINS]
        # self.set_valves([False for _ in len(self.NUM_VALVES)])

    def close_valves(self, verbose=False):
        for i in range(8):
            # self.sts[i].value = 0
            self.sts[i].value = 0 if i not in self.BROKEN_VALVES else 1
        
        # pulse enable
        self.mcp.gpio = self.mcp.gpio | 0b1010101010101010
        time.sleep(self.PULSE_TIME)
        self.mcp.gpio = self.mcp.gpio & 0b0101010101010101
        
        if verbose:
            print(self.get_valve_state())
        
    def open_valves(self, verbose=False):
        for i in range(8):
            # self.sts[i].value = 1
            self.sts[i].value = 1 if i not in self.BROKEN_VALVES else 0
        
        # pulse enable
        self.mcp.gpio = self.mcp.gpio | 0b1010101010101010
        time.sleep(self.PULSE_TIME)
        self.mcp.gpio = self.mcp.gpio & 0b0101010101010101
        
        if verbose:
            print(self.get_valve_state())
            
    def change_valve_state(self, valve):
        # toggle
        self.sts[valve].value = 1 if self.sts[valve].value == 0 else 0
        
        # pulse enable
        self.mcp.gpio = self.mcp.gpio | 0b1010101010101010
        time.sleep(self.PULSE_TIME)
        self.mcp.gpio = self.mcp.gpio & 0b0101010101010101
        
    def set_valves(self, states, verbose=False):
        if len(states)>self.NUM_VALVES:
            warnings.warn("number of states exceeds number of valves")

            
        # overwrite states
        for i, st in enumerate(states):
            # self.sts[i].value = st
            self.sts[i].value = st if i not in self.BROKEN_VALVES else not bool(st)
        
        # pulse enable
        self.mcp.gpio = self.mcp.gpio | 0b1010101010101010
        time.sleep(self.PULSE_TIME)
        self.mcp.gpio = self.mcp.gpio & 0b0101010101010101
        
        # equivalently (though not as syncronized)
        #for i in len(states):
        #    self.ens[i].value = True
        #time.sleep(self.PULSE_TIME)
        #for i in len(states):
        #    self.ens[i].value = False
        
        if verbose:
            print(self.get_valve_state())
        
    def get_valve_state(self):
        # return ' '.join(['1' if s.value else '0' for s in self.sts])
        return ' '.join(['1' if s.value and s not in self.BROKEN_VALVES else '0' if s not in self.BROKEN_VALVES else '1' for s in self.sts])
        
    def get_temperature(self, verbose=False):
        # space here for possible offset calibration
        temp = self.tc.temperature
        #print(temp)
        if verbose: print('Temperature: '+str(temp))
        return temp
        
    def show_temp(self, sec, verbose=False):
        self.stop_heater()
        start_time = time.time()
        end_time = start_time + sec
        
        while time.time() < end_time:
            print(self.get_temperature())
            time.sleep(0.5)
    
    #def heat_to(self, temp=37):
    #    while True:
    #        if self.get_temperature() < 37:
    #            self.set_heater(1)
    #        elif self.get_temperature() >= 37:
    #            self.set_heater(0)
    #        print(self.get_temperature()) 
    
    
    def set_heater(self, duty, period=1):
        #print('In start heat')
        '''
        Parameters
        ----------
        duty : float
            Duty cycle to set for PWM on the interval [0,1]
        period : float, optional
            1/frequency at which pwm is conducted. The default is 1 second.

        Returns
        -------
        None.
        '''
        #stop current heater
        self.stop_heater()
        

        
        #calc new parameters
        if duty<0 or duty>1: raise ValueError('duty must be on [0,1]')
        on_time = duty*period
        off_time = period - on_time        
        #set new heater pwm
        self.heater_thread = InterruptThread(target=self._pwm_period, args=[on_time, off_time])
        self.heater_thread.start()
        
        
    def stop_heater(self):
        if self.heater_thread is not None and self.heater_thread.is_alive():
            self.heater_thread.interrupt()
            self.heater_thread.join()

    
    def _pwm_period(self, on, off):
        '''Executes a single period of the heater pin. Intended for use as the
        target of an utils.InterruptThread'''
        self.heat.value = True
        time.sleep(on)
        self.heat.value = False
        time.sleep(off)
    
    
    def heater_pid(self, setpoint=37, sample_period=1):
        #print('in heater pid')
        self.stop_heater()
        start_time = time.time()
        end_time = start_time + 900

        pid = PID(0.06, 0.001, 0.05, setpoint=setpoint)
        pid.output_limits = (0,1)
        pid.sample_time = sample_period
        temp = self.get_temperature()
        
        while time.time() < end_time:
            # Compute new output from the PID according to the systems current value
            control = pid(temp)
            print(control)
            self.set_heater(control)
            temp = self.get_temperature()
            print(temp)
                
        self.set_heater(0)

    
    def thread_pid(self, sec, setpoint=37, sample_period=1):
        start_time = time.time()
        end_time = start_time + sec
        pid = PID(0.06, 0.001, 0.05, setpoint=setpoint)
        pid.output_limits = (0, 1)
        pid.sample_time = sample_period
        stop = [False]
        
        def pid_loop():
            temp = self.get_temperature()
            while time.time() < end_time:
                control = pid(temp)
                self.set_heater(control)
                temp = self.get_temperature()
            if stop[0]:
                self.set_heater(0)
                return
            self.set_heater(0)
            print("\npid thread finished")
            stop[0] = True
        
        if stop[0]:
            self.set_heater(0)
            return

        heater_thread = InterruptThread(target=pid_loop)
        heater_thread.start()
     
     
    def start_thread_pid(self, temp):
        self.stop_heater()
        self.run_thread = True
        self.pid_thread = threading.Thread(target=self.notime_thread_pid, args=(temp,))
        self.pid_thread.start()

    def notime_thread_pid(self, setpoint, sample_period=1):
        pid = PID(0.06, 0.001, 0.05, setpoint)
        pid.output_limits = (0, 1)
        pid.sample_time = sample_period
        
        while self.run_thread:
            temp = self.get_temperature()
            control = pid(temp)
            self.set_heater(control)
            time.sleep(sample_period)
        
        self.set_heater(0)

    def stop_thread(self):
        self.run_thread = False
        if self.pid_thread and self.pid_thread.is_alive():
            self.pid_thread.join()
        self.stop_heater()
        self.set_heater(0)
        
    def shutdown(self):
        self.set_heater(0)
        self.stop_heater()
        raise SystemExit
                
def i2c_scan(i2c, verbose=True):
    '''utility function to check available I2C devices'''

    i2c = busio.I2C(board.SCL, board.SDA)
    mcp = None

    for i in i2c.scan():
        if verbose:
            print("attempting connection at address "+str(i)+" ...")
        try:
            mcp = MCP23017(i2c, address=i)
            if verbose: print("success!")
            break
        except ValueError:
            if verbose: print("connection failure")
    
    if mcp is None:
        if verbose: print("Could not establish i2c connection.")
    
    return mcp
    
def test_TP3(mcp):
    pin0 = mcp.get_pin(0)
    
    print('begin TP3 test...')
    for _ in range(10):
        pin0.value = True
        time.sleep(3)
        pin0.value = False
        time.sleep(3)
    
    print('TP3 test concluded')


def test_V1(mcp):
    en0 = mcp.get_pin(0)
    st0 = mcp.get_pin(8)

    for _ in range(10):
        time.sleep(2)
        en0.value = not en0.value
        time.sleep(2)
        st0.value = not st0.value
        en0.value = not en0.value
        

class Valve():
    
    def __init__(self, en, st):
        self.en, self.st = en, st
        self._state = True # is this guaranteed? should set it not instead
        
    def set_high(self):
        self.en.value = True 
    
    @property
    def state(self):
        return self._state
    
    @state.setter
    def state(self, b):
        if b:
            self.set_high()
        else:
            self.set_low()
        self._state = b


    
        
if __name__ == '__main__':

    mcp = mcp_connect(i2c_connect())
    
    test_TP3(mcp)
