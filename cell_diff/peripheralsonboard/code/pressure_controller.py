# pressure_controller.py
# sends commands to pressure controller
# 
# tested with Python 3.5.1 (IDE Eclipse V4.5.2 + Pydev V5.0.0)
# add python_xx and python_xx/DLL to the project path
# coding: utf8

import sys, datetime
from ctypes import c_int32, c_double, byref

# Elveflow library needs to be added to PATH
try:
    sys.path.append(r'C:/Users/EVOS/Documents/ESI_V3_07_02/ESI_V3_07_02/SDK_V3_07_02/SDK_V3_07_02/Python_64/DLL64')#add the path of the library here
    sys.path.append(r'C:/Users/EVOS/Documents/ESI_V3_07_02/ESI_V3_07_02/SDK_V3_07_02/SDK_V3_07_02/Python_64')#add the path of the LoadElveflow.py
    from Elveflow64 import Elveflow_Calibration_Default, Elveflow_Calibration_Load, \
    Elveflow_Calibration_Save, OB1_Initialization, OB1_Get_Press, OB1_Set_Press, \
    OB1_Calib
except:
    print("Failed to add Elveflow DLL to path.")


class OB1_Pressure_Controller_Dummy():
    
    def set_pressure(self, p, ch, verbose=False):
        if verbose: print("Set Pressure {}: {}".format(ch,p))
        
    def get_pressure(self, ch, verbose=False):
        if verbose: print("Get Pressure {}: {}".format(ch,0))
        return 0

class OB1_Pressure_Controller():
    def __init__(self, iid='USB0::0x3923::0x7166::01B7DFC3::RAW', calibration='default'):
        self.instr_id = c_int32() # Instrument ID
        self.error = OB1_Initialization(iid.encode('ascii'),1,1,0,0,byref(self.instr_id))
        
        self.calib = (c_double*1000)()
        
        self.init_calibration(calibration)
        
    def init_calibration(self, calibration):

        if calibration=='default':
            self.error = Elveflow_Calibration_Default(byref(self.calib),1000)
            
        elif calibration=='new':
            OB1_Calib(self.instr_id.value, self.calib, 1000)
            calib_path = 'Cal_'+datetime.date.today().isoformat()
            self.error = Elveflow_Calibration_Save(calib_path.encode('ascii'), byref(self.calib), 1000)
            print ('calib saved in {}'.format(calib_path))
            
        else:
            calib_path = calibration
            self.error = Elveflow_Calibration_Load(calibration.encode('ascii'), byref(self.calib), 1000)
    
    def set_pressure(self, p, ch, verbose=False):
        if verbose: print("Set Pressure {}: {}".format(ch,p))
        ch = c_int32(ch)
        p = c_double(p)
        self.error = OB1_Set_Press(self.instr_id.value, ch, p, byref(self.calib), 1000)
        
    def get_pressure(self, ch, verbose=False):
        ch = c_int32(ch)
        p = c_double()
        self.error = OB1_Get_Press(self.instr_id.value, ch, 1, byref(self.calib),byref(p), 1000)#Acquire_data=1 -> read all the analog values
        if verbose: print("Get Pressure {}: {}".format(ch,p))
        return p.value
        
