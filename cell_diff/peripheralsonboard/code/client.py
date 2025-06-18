# client.py
# sends commands to server
# look at print_commands() for overview of commands (at bottom)
#
# main file: controller.py, interface file: interface.py, 
# pressure controller: pressure_controller.py, 
# frequency controller: eis_board_class.py, server file: server_backend.py
import socket
import time
import threading
import re
from collections import deque
import atexit
from pressure_controller import OB1_Pressure_Controller, OB1_Pressure_Controller_Dummy
import pressure_controller
from eis_board_class import Eis_Board
import math

class Client:
    def __init__(self, ip, use_pressure, pressure_settings={}):
        # connects to server via ip
        self.ip = ip
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((ip, 8080))
        print("CLIENT: connected")
        print("Use print_commands() to print function desciptions")
        
        # initilaze eis_board class
        self.eis_board = Eis_Board(self.client)
        
        # closes valves
        self.client.send("cv*".encode())
        # stops heats
        self.client.send("stop_heat*".encode())

        self.temp_to_set_to = 0 # temp set by user
        self.p1_to_set_to = 0 # pressure 1 set by user
        self.p2_to_set_to = 0 # pressure 2 set by user
        self.current_temp = 0 # most recent temp stored
        self.current_p1 = 0 # most recent pressure 1 stored
        self.current_p2 = 0 # most recent pressure 2 stored
        self.current_ny = 0 # most recent nyquist stored
        self.current_R = 0 # most recent R stored
        self.current_theta = 0 # most recent theta stored
        self.all_temps = deque(maxlen=1000) # las 1000 temps stored
        self.all_p1 = deque(maxlen=1000) # last 1000 pressure 1 stored
        self.all_p2 = deque(maxlen=1000) # last 1000 pressure 2 stored
        self.all_R = deque(maxlen=1000) # last 1000 R values stored
        self.all_theta = deque(maxlen=1000) # last 1000 theta values stored
        self.x = 0 # most recent x
        self.y = 0 # most recent y 
        self.f = 0 # most recent frequency
        self.all_x = deque(maxlen=1000) # last 1000 x values stored
        self.all_y = deque(maxlen=1000) # last 1000 x values stored
        self.all_f = deque(maxlen=1000) # last 1000 frequencys values stored
        self.current_valves = [] # current valve states
        self.current_sleep_time = 0 # current time to sleep from file
        self.sample_time = 1000 # time interval to get board info
        
        self.stop_reading_file = True # continue reading file until True
        self.input_file_thread = None # input file thread
        self.output_file_thread = None # ouput file thread
        
        # sets defualt output file
        self.output_filepath = "board_info.txt"

        self.pressure_controller = OB1_Pressure_Controller(**pressure_settings)\
            if use_pressure else OB1_Pressure_Controller_Dummy()
        
        atexit.register(self.close_connection) # calls close_connection if
                                               # program terminates 
                                               
    # starts sweep
    def start_frequency(self):
        self.eis_board.start_frequency()
        self.eis_board.single_frequency()
      
    # stops sweep  
    def stop_frequency(self):
        self.eis_board.stop_frequency()
        
    # sets frequency
    def set_freq(self, val):
        self.eis_board.set_freq(val)
     
    # sends message to server   
    def send_message(self, msg):
        self.client.send((str(msg) + "*").encode())
        
    # toggles valve state
    def toggle_valve(self, valve):
        self.client.send(f"c{valve}*".encode())
        
    # set vavle states
    def set_valves(self, valves):
        self.client.send("set_valves*".encode())
        self.client.send((str(valves) + "*").encode())
    
    # sets heat 
    def set_heat(self):
        self.client.send("set_temp*".encode())
        self.client.send((str(self.temp_to_set_to) + '*').encode())
        
    # sets heat and takes in temp as arguement
    def set_heat_arg(self, temp):
        self.client.send("set_temp*".encode())
        self.client.send((str(temp) + '*').encode())
    
    # stops heat
    def stop_heat(self):
        self.client.send("stop_heat*".encode())

    # sends pressure 1 to controller
    def send_pressure1_client(self, p1):
        self.pressure_controller.set_pressure(float(p1), 1)
        
    # sends pressure 2 to controller
    def send_pressure2_client(self, p2):
        self.pressure_controller.set_pressure(float(p2), 2)
   
    # returns True if file is correctlty formatted, False otherwise 
    # correct format: p1 p2 time v1 v2 v3 v4 v5 v6 v7 v8\n
    # lines with '#' will be ignored
    def file_formatted(self, file_path):
        if file_path:
            with open(file_path, "r") as file:
                for line in file:
                    if line.startswith("#"):
                        continue
                    numbers = line.split()
                    if len(numbers) != 11 or not all(num.replace('.', '').isdigit() for num in numbers[:3]) or float(numbers[2]) < 0 or not all(num in ['0', '1'] for num in numbers[-8:]):
                        return False
            return True
        else:
            return False

    
    # starts file reading thread
    def start_file_thread(self, file_path):
        with open(file_path, "r") as file:
            file_content = file.read()
            self.stop_reading_file = False
            self.input_file_thread = threading.Thread(target=self.read_lines, args=(file_content,))
            self.input_file_thread.start()
            self.output_file_thread = threading.Thread(target=self.output_data, args=(file_content,))
            self.output_file_thread.start()
    
    # performs commands from file
    def read_lines(self, input_file):
        input_file = input_file.split('\n')
        while not self.stop_reading_file: 
            for line in input_file:
                if self.stop_reading_file:
                    break
                if line.startswith("#"):
                    continue
                if line.strip():
                    numbers = line.strip().split()
                    
                    # sets valves
                    self.current_valves = numbers[3:]
                    self.client.send((' '.join(self.current_valves) + "*").encode())
                    
                    # sets time
                    self.current_sleep_time = float(numbers[2])
                    
                    # sets pressure
                    self.p1_to_set_to= numbers[0]
                    self.p2_to_set_to = numbers[1]
                    self.send_pressure1_client(numbers[0])
                    self.send_pressure2_client(numbers[1])
                
                    self.current_sleep_time = float(self.current_sleep_time)
            
                    for _ in range(int(self.current_sleep_time)):
                        if self.stop_reading_file:
                            break
                        
                        time.sleep(1)
            
                    # Sleep for the remaining seconds
                    time.sleep(self.current_sleep_time % 1)
                
                    # time.sleep(float(self.current_sleep_time))
               
    # outputs board info to file     
    # output format: temp p1 p2 freq x y v1 v2 v3 v4 v5 v6 v7 v8    
    def output_data(self, input_file):
        sample_time = self.sample_time
        with open(self.output_filepath, "w") as output_file:
            output_file.write("Sample time: " + str(float(sample_time)/1000) 
                              + " s | File Format: TEMP P1 P2 FREQ X Y VALVES\n")
            
            while not self.stop_reading_file: 
                line = ' '.join((str(self.current_temp),
                                 str(self.pressure_controller.get_pressure(1)),
                                 str(self.pressure_controller.get_pressure(2)),
                                 str(self.f),
                                 str(self.x),
                                 str(self.y),
                                 str(self.current_valves)
                                 )) + '\n'
                output_file.write(line)
                
                time.sleep(float(sample_time)/1000)
                     
    # stops file reading thread and sends message to stop reading file to server  
    def stop_file_thread(self):
        if self.output_file_thread:
            self.stop_reading_file = True
            self.output_file_thread.join() 
            self.output_file_thread = None
            
    # prints temp for input time
    def show_temp(self, sec):
            end_time = time.time() + sec
            
            while time.time() < end_time:
                self.update_values()
                print(self.current_temp)
                time.sleep(0.5)
            
    # sends command to sevrer to get temp, stores temp if formatted correctly
    def update_values(self, verbose=False):
        self.client.send('get_values*'.encode())
        message = self.client.recv(4096).decode() 
        
        # f represents frequency          
        temp, f, x, y = message.split(',')
        
        # sets variables for current values and append to list of all values
        self.x = float(x)
        self.y = float(y)
        self.f = float(f)
        self.all_x.append(float(self.x))
        self.all_y.append(float(self.y))
        self.all_f.append(float(self.f))
        
        # sets temp if formatted correctly
        self.current_temp = temp
        self.all_temps.append(float(temp))
        
        # calculates R and appends value
        self.current_R = math.sqrt(self.x ** 2 + self.y ** 2)
        self.all_R.append(float(self.current_R))
        
        # calculated theta and appends value
        if self.y != 0 and self.x != 0: # makes sure you do not divide by 0
            self.current_theta = math.atan(self.y/self.x)
        else:
            self.current_theta = 0
            
        self.all_theta.append(float(self.current_theta))
        
        # prints values to stdout
        if verbose: print("Temp:", self.current_temp, "Freq:", self.f, "X:", self.x, "Y:", self.y)
            
    # gets pressures from controller and stores
    def update_pressure(self, verbose=False):
        self.current_p1 = self.pressure_controller.get_pressure(1)
        self.current_p2 = self.pressure_controller.get_pressure(2)
        
        p1 = self.current_p1 
        p2 = self.current_p2
        self.all_p1.append(float(p1))
        self.all_p2.append(float(p2))
        self.current_p1 = round(float(p1), 1)
        self.current_p2 = round(float(p2), 1)
        if verbose: print("p1: " + str(self.current_p1) + " p2: " + str(self.current_p2))
        
        
    # tells server client is terminated and closes client connection
    # stops heat and frequency threads
    def close_connection(self):
        self.client.send('stop_heat*'.encode())
        self.stop_file_thread()
        self.client.send('stop_heat*'.encode())
        self.client.send('stop_freq*'.encode())
        self.client.send('stop_heat*'.encode())
        print("CLIENT: disconnected")
        self.client.close()
        
    # tells server to terminate and closes client connection
    def kill_server(self):
        self.client.send('quit*'.encode())
        self.client.close()
        
# prints function descriptions
    def print_commands(self):
        """
        Prints function descriptions:

        Valve Control:
        - toggle_valve(valve): Toggles the state of a valve.
            valve (int): The valve number to toggle.

        - set_valves(valves): Sets the state of multiple valves using a string of valve states (1 to open, 0 to close).
            valves (str): A string containing space-separated valve states (e.g., "1 0 1 0 1 1 0 0").

        Heat Control:
        - set_heat(): Sets the heat to the temperature value specified by temp_to_set_to.

        - set_heat_arg(temp): Sets the heat to the given temperature value.
            temp (int): The temperature value to set the heat to.

        - stop_heat(): Stops the heating process.

        Pressure Control:
        - send_pressure1_client(p1): Sends pressure value p1 to the pressure controller channel 1.
            p1 (float): The pressure value to set for channel 1.

        - send_pressure2_client(p2): Sends pressure value p2 to the pressure controller channel 2.
            p2 (float): The pressure value to set for channel 2.
            
        Frequency Control: 
        - start_frequency(): starts single frequency sweep
       
        - stop_frequency(): stops sweep
        
        - set_freq(val): sets frequency
            val (int): frequency to set to
                    
        File Operations:
        - file_formatted(file_path): Checks if the file at the given path is correctly formatted.
            file_path (str): The path of the file to check.

        - start_file_thread(file_path): Reads the file, outputs board info to output_filepath, and starts threads.
            file_path (str): The path of the file to read.

        - read_lines(input_file): Reads the input file and performs the specified commands.
            input_file (str): The content of the input file as a string.

        - output_data(input_file): Continuously outputs board data to output_filepath.
            input_file (str): The content of the input file as a string.

        - stop_file_thread(): Stops the file reading and writing threads.

        Other Commands:
        - show_temp(sec): Displays the current temperature for the given time in seconds.
            sec (int): The time duration in seconds to display the temperature.

        - update_values(): Retrieves and prints the current temp, freq, x, and y.

        - update_pressure(): Retrieves and prints the current pressures.

        - close_connection(): Closes the client and server connection.
        
        - kill_server(): Shutsdown server.
        """
        
        print("*********************************************************************************************************************")
        print("* Valve Control:")
        print("* - toggle_valve(valve): Toggles the state of a valve.")
        print("*                      valve (int): The valve number to toggle.")
        print("*")
        print("* - set_valves(valves): Sets the state of multiple valves using a string of valve states (1 to open, 0 to close).")
        print("*                      valves (str): A string containing space-separated valve states (e.g., '1 0 1 0 1 1 0 0').")
        print("*")
        print("* Heat Control:")
        print("* - set_heat(): Sets the heat to the temperature value specified by temp_to_set_to.")
        print("*")
        print("* - set_heat_arg(temp): Sets the heat to the given temperature value.")
        print("*                      temp (int): The temperature value to set the heat to.")
        print("*")
        print("* - stop_heat(): Stops the heating process.")
        print("*")
        print("* Pressure Control:")
        print("* - send_pressure1_client(p1): Sends pressure value p1 to the pressure controller channel 1.")
        print("*                             p1 (float): The pressure value to set for channel 1.")
        print("*")
        print("* - send_pressure2_client(p2): Sends pressure value p2 to the pressure controller channel 2.")
        print("*                             p2 (float): The pressure value to set for channel 2.")
        print("*")
        print("* Frequency Control:") 
        print("* - start_frequency(): starts single frequency sweep")
        print("*")
        print("* - stop_frequency(): stops sweep")
        print("*")
        print("* - set_freq(val): sets frequency")
        print("*    val (int): frequency to set to")
        print("*")
        print("* File Operations:")
        print("* - file_formatted(file_path): Checks if the file at the given path is correctly formatted.")
        print("*                              file_path (str): The path of the file to check.")
        print("*")
        print("* - start_file_thread(file_path): Reads the file_path, outputs board info to output_filepath, and starts threads.")
        print("*                                 file_path (str): The path of the file to read.")
        print("*")
        print("* - stop_file_thread(): Stops the file reading and writing threads.")
        print("*")
        print("* Other Commands:")
        print("* - show_temp(sec): Displays the current temperature for the given time in seconds.")
        print("*                   sec (int): The time duration in seconds to display the temperature.")
        print("*")
        print("* - update_values(): Retrieves and prints the current temp, freq, x, and y.")
        print("*")
        print("* - update_pressure(): Retrieves and prints the current pressures.")
        print("*")
        print("* - close_connection(): Closes the client and server connection.")
        print("*")
        print("* - kill_server(): Shutsdown server.")
        print("*********************************************************************************************************************")