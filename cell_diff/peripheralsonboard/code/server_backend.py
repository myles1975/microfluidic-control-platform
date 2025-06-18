# server_backend.py
#
# Purpose: recieved commands from CPU to alter and analyze state
# of board

# -*- coding: utf-8 -*-
"""
Created on Tue May 30 14:37:22 2023

@author: EVOS
"""

from labonscope import LoS
# from eis_board import eis_board
import socket
import time
import threading

import os
import sys

sys.path.append(os.path.expanduser('~/Documents/Python/eisb'))

from ad5933 import ad5933
    
class LoSServer():
        
    def __init__(self, *args, **kwargs):
        self.los = LoS(*args, **kwargs)
        self.ad = ad5933()
        
    def run(self, ip, port=8080):
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as serv:
            serv.bind((ip, port))
            serv.listen(5)
            print("server started at {}/{}".format(ip,port))
                   
            # sends temp to client
            def values():
                conn.sendall((str(self.los.get_temperature()) + "," + str(self.ad.curr_f) + ',' + str(self.ad.curr_r) + ',' + str(self.ad.curr_i)).encode())
                                        
            # sets valves to input
            def valves():
                valves = conn.recv(4096).decode()
                states = [int(x) for x in valves.split()]
                self.los.set_valves(states)
                        
            # stops heater thread
            def stop():
                self.los.stop_thread()

            # starts heater thread
            def start_heat_thread():
                stop()
                msg = conn.recv(4096).decode()
                messages = msg.split('*')
                
                for message in messages:
                    if message in commands:
                        commands[message]()
                    elif message.isdigit():
                        self.los.start_thread_pid(int(message))  
                        
            # set valve states
            def set_valves():
                msg = conn.recv(4096).decode()
                messages = msg.split('*')    
                
                for message in messages:
                    if message in commands:
                        commands[message]()
                    elif message:   
                        states = [int(x) for x in message.split() if x.isdigit()]
                        self.los.set_valves(states) 
                
            # sets start freq value
            def start_value():
                
                msg = conn.recv(4096).decode()
                messages = msg.split('*')   
                
                for message in messages:
                    if message in commands:
                        commands[message]()
                    elif message:
                        self.ad.start_freq = float(message)
                        self.ad._write_start_freq()    
            
            # start frequency sweep
            def start_freq_t():
                self.ad = ad5933()
                self.ad.thread_bool = True
                self.ad.start_thread()
                
            # stops frequency sweep
            def stop_freq_thread():
                self.ad.thread_bool = False
                self.ad = None
                self.ad = ad5933()
            
            # starts single frequency mode
            def single_freq_mode():
                self.ad.single_frequency_mode(1000)
                
            # shutsdown server
            def quit_program():
                print('Server Shutdown')
                stop()
                stop_freq_thread()
                self.los.shutdown()
                sys.exit(0)
            
            # maps commands to functions
            commands = {
                'cv': self.los.close_valves,
                'ov': self.los.open_valves,
                'valves': valves,
                'set_valves': set_valves,
                'c1': lambda: self.los.change_valve_state(0),
                'c2': lambda: self.los.change_valve_state(1),
                'c3': lambda: self.los.change_valve_state(2),
                'c4': lambda: self.los.change_valve_state(3),
                'c5': lambda: self.los.change_valve_state(4),
                'c6': lambda: self.los.change_valve_state(5),
                'c7': lambda: self.los.change_valve_state(6),
                'c8': lambda: self.los.change_valve_state(7),
                'get_values': values,
                'stop_heat': stop,
                'set_temp': start_heat_thread,
                'start': start_value,
                'quit': quit_program,
                'start_freq_t': start_freq_t,
                'stop_freq': stop_freq_thread,
                'single_freq_mode': single_freq_mode,
            }
           
            # recieves commands from clients and calls corresponding 
            # functions
            while True:
                # establish connection
                conn, addr = serv.accept()
              
                from_client = ''
                print("SERVER: connection to client established")

            
                with conn:    
                    prev_msg = ''
                    while True:
                        data = conn.recv(4096).decode()
                        if not data: break
                        from_client = ''
                        from_client += data
                        print("Recieved: " + from_client)
                        messages = from_client.split('*')
                        for message in messages:
                            
                            if message in commands:
                                commands[message]()
                                
                            elif message != prev_msg and message != '':
                                states = [int(x) for x in message.split() if x.isdigit()]
                                self.los.set_valves(states)
                            prev_msg = message

                        # checks if temp is too high and turns of heater
                        if int(self.los.get_temperature()) > 55:
                            stop()
                        
    
if __name__ == "__main__":
	
    ip = ""
    if len(sys.argv) != 1:
        ip = sys.argv[1]
    else:
        print("Missing arguement. Input ip address as commandline arguement.")
        exit(0)
    
    # "127.0.0.1" should work here too?
    
    #run_server(ip)
    los_server = LoSServer()
    los_server.run(ip)
