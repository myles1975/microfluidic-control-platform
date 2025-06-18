# interface.py 
# interface for client
# 
# main file: controller.py, client file: client.py, 
# pressure controller: pressure_controller.py, server file: server_backend.py

from random import sample
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
from matplotlib.figure import Figure
from matplotlib import style
import threading
import time
from client import Client

class Interface:
    def __init__(self, client):
        self.client = client # sets client
        self.file_thread = None # thread to read file
        self.stop_thread = True # boolean to stop file reading thread

        self.main_window = tk.Tk() # creates main_window
        self.main_window.configure(bg="#000000") # sets background color

        self.create_graphs() # initializes graphs
        self.create_widgets() # creates buttons
        self.set_frequency_button.config(state=tk.DISABLED)

        self.get_current_temperature() # updates temp for sample time
        self.get_current_pressures() # updates pressure for sample time

        self.main_window.geometry("1400x900") # sets window size
        self.main_window.mainloop() # begins main_window loop

    # initializes temp and pressure graphs
    def create_graphs(self):
        
        self.main_graph_frame = tk.Frame(self.main_window)
        self.main_graph_frame.pack(fill=tk.BOTH, expand=True)

        self.temp_graph = Figure(figsize=(4, 3), dpi=100)
        self.temp_ax = self.temp_graph.add_subplot(111)
        self.temp_canvas = FigureCanvasTkAgg(self.temp_graph, master=self.main_graph_frame)
        self.temp_canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.pressure_graph = Figure(figsize=(4, 3), dpi=100)
        self.pressure_ax = self.pressure_graph.add_subplot(111)
        self.pressure_canvas = FigureCanvasTkAgg(self.pressure_graph, master=self.main_graph_frame)
        self.pressure_canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.impedence_graph = Figure(figsize=(4, 3), dpi=100)
        self.impedence_ax = self.impedence_graph.add_subplot(111)
        self.impedence_canvas = FigureCanvasTkAgg(self.impedence_graph, master=self.main_graph_frame)
        self.impedence_canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.ani_graphs = animation.FuncAnimation(self.temp_graph, self.update_graphs, interval=int(self.client.sample_time))


    def create_widgets(self):
        
        valve_button_frame = tk.Frame(self.main_window, bg="#000000")
        valve_button_frame.pack(pady=5)
        heat_button_frame = tk.Frame(self.main_window, bg="#000000")
        heat_button_frame.pack(pady=10)
        pressure_button_frame = tk.Frame(self.main_window, bg="#000000")
        pressure_button_frame.pack(pady=10)
        sample_button_frame = tk.Frame(self.main_window, bg="#000000")
        sample_button_frame.pack(pady=10)
        select_input_file_button_frame = tk.Frame(self.main_window, bg="#000000")
        select_input_file_button_frame.pack(pady=5)
        select_output_file_button_frame = tk.Frame(self.main_window, bg="#000000")
        select_output_file_button_frame.pack(pady=5)
        hold_frame = tk.Frame(self.main_window, bg="#000000")
        hold_frame.pack(pady=10)
        read_file_button_frame = tk.Frame(self.main_window, bg="#000000")
        read_file_button_frame.pack(pady=10) 

        self.valve_buttons = {}
        for i in range(1, 9):
            button = tk.Button(
                valve_button_frame,
                text=f"Valve {i}",
                command=lambda val=i: self.toggle_valve_color(val),
                font=("Arial", 18),
                bg="#555555",
                fg="#000000"
            )
            button.pack(side="left", padx=1)
            self.valve_buttons[i] = button

        self.set_temp_text = self.create_entry_with_default_text("Celsius", heat_button_frame)
        self.set_temp_text.pack(side=tk.LEFT, padx=5)
        self.set_temp_text.bind("<Return>", lambda event: self.toggle_set_heat())

        self.set_heat_button = tk.Button(
            heat_button_frame,
            text="Set Heat",
            command=self.toggle_set_heat,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000"
        )
        self.set_heat_button.pack(side=tk.LEFT, padx=5)

        self.stop_heat_button = tk.Button(
            heat_button_frame,
            text="Stop Heat",
            command=self.toggle_stop_heat,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000",
            state=tk.DISABLED
        )
        self.stop_heat_button.pack(side=tk.LEFT, padx=5)

        self.set_p1_text = self.create_entry_with_default_text("Pressure 1", pressure_button_frame)
        self.set_p1_text.pack(side=tk.LEFT, padx=5)
        self.set_p1_text.bind("<Return>", lambda event: self.send_pressures())
        
        self.set_p2_text = self.create_entry_with_default_text("Pressure 2", pressure_button_frame)
        self.set_p2_text.pack(side=tk.LEFT, padx=5)
        self.set_p2_text.bind("<Return>", lambda event: self.send_pressures())

        self.set_p_button = tk.Button(
            pressure_button_frame,
            text="Set Pressures",
            command=self.send_pressures,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000"
        )
        self.set_p_button.pack(side=tk.LEFT, padx=5)
        
        self.sample_time_text = self.create_entry_with_default_text("Seconds", sample_button_frame)
        self.sample_time_text.pack(side=tk.LEFT, padx=5)
        self.sample_time_text.bind("<Return>", lambda event: self.get_sample_time())
        
        self.set_sample_time_button = tk.Button(
            sample_button_frame,
            text="Set Sample Time",
            command=self.get_sample_time,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000"
        )
        self.set_sample_time_button.pack(side=tk.LEFT, padx=5)
        
        self.frequency_text = self.create_entry_with_default_text("kHz", sample_button_frame)
        self.frequency_text.pack(side=tk.LEFT, padx=5)
        
        self.set_frequency_button = tk.Button(
            sample_button_frame,
            text="Set Frequency",
            command=self.set_frequency,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000"
        )
        self.set_frequency_button.pack(side=tk.LEFT, padx=5)
        
        self.toggle_frequency_button = tk.Button(
            sample_button_frame,
            text="Start Sweep",
            command=self.toggle_frequency,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000"
        )
        self.toggle_frequency_button.pack(side=tk.LEFT, padx=5)

        self.select_file_button = tk.Button(
            select_input_file_button_frame,
            text="Select Input File",
            command=self.scan_file,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000"
        )
        self.select_file_button.pack(side=tk.LEFT, padx=5)
        
        self.input_file_label = tk.Label(
            select_input_file_button_frame,
            text="No input file selected",
            font=("Arial", 12)
        )
        self.input_file_label.pack(side=tk.LEFT, padx=5)
        
        self.output_file_button = tk.Button(
            select_output_file_button_frame,
            text="Select Ouput File",
            command=self.output_file,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000"
        )
        self.output_file_button.pack(side=tk.LEFT, padx=5)
        
        self.output_file_label = tk.Label(
            select_output_file_button_frame,
            text="No output file selected",
            font=("Arial", 12)
        )
        self.output_file_label.pack(side=tk.LEFT, padx=5)
        
        self.countdown_label = tk.Label(
            hold_frame,
            text="Hold Time: 0",
            font=("Arial", 18),
            fg="#FFFFFF",
            bg="#000000"
        )
        self.countdown_label.pack()

        self.execute_file_button = tk.Button(
            read_file_button_frame,
            text="Execute",
            command=self.execute_file,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000",
            state=tk.DISABLED
        )
        self.execute_file_button.pack(side=tk.LEFT, padx=5)

        self.stop_reading_file_button = tk.Button(
            read_file_button_frame,
            text="Stop Reading File",
            command=self.stop_reading_file_func,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000",
            state=tk.DISABLED
        )
        self.stop_reading_file_button.pack(side=tk.LEFT, padx=5)

        self.temperature_label = tk.Label(
            self.main_window,
            text="Temperature: -°C",
            font=("Arial", 18),
            fg="#000000",
            bg="#000000"
        )
        self.temperature_label.pack()

        self.pressure_label = tk.Label(
            self.main_window,
            text="Current Pressure: - psi",
            font=("Arial", 18),
            fg="#000000",
            bg="#000000"
        )
        self.pressure_label.pack()

        self.quit_button = tk.Button(
            self.main_window,
            text="Quit Program",
            command=self.quit_program,
            font=("Arial", 18),
            bg="#555555",
            fg="#000000"
        )
        self.quit_button.pack(pady=15)

        self.error_message = tk.Label(
            self.main_window,
            text="",
            font=("Arial", 18),
            fg="#FF0000",
            bg="#000000"
        )
        self.error_message.pack(pady=2)

    # creates place holder text in text boxes
    def create_entry_with_default_text(self, default_text, place):
        entry = tk.Entry(
            place,
            font=("Arial", 18),
            bg="#555555",
            fg="#AAAAAA"
        )
        entry.insert(0, default_text)
        entry.bind("<FocusIn>", self.on_entry_click)
        entry.bind("<FocusOut>", self.on_focus_out)
        return entry

    # removes place holder text in text boxes
    def on_entry_click(self, event):
        event.widget.delete(0, "end")
        event.widget.config(fg="#FFFFFF")

    # creates place holder text in text boxes
    def on_focus_out(self, event):
        widget = event.widget
        if widget.get() == "":
            default_text = ""
            if widget is self.set_p1_text:
                default_text = f"P1 Set To: {self.client.p1_to_set_to} psi"
            elif widget is self.set_p2_text:
                default_text = f"P2 Set To: {self.client.p2_to_set_to} psi"
            elif widget is self.set_temp_text:
                default_text = f"Temp Set To: {self.client.temp_to_set_to}°C"
            elif widget is self.sample_time_text:
                sec = float(self.client.sample_time)/1000
                if sec == 1:
                    default_text = f"Time Set To: {sec} Second"
                else:
                    default_text = f"Time Set To: {sec} Seconds"
            elif widget is self.frequency_text:
                default_text = f"Frequency: {self.client.f} kHz" 
                
            widget.insert(0, default_text)
            widget.config(fg="#AAAAAA")
        
    # live temp and pressure graph (updates every second, displays past minute)
    def update_graphs(self, i):
        all_temps_list = list(self.client.all_temps)[-100:]
        all_p1_list = list(self.client.all_p1)[-100:]
        all_p2_list = list(self.client.all_p2)[-100:]
        all_R_list = list(self.client.all_R)[-100:]
        all_theta_list = list(self.client.all_theta)[-100:]

        xs = list(range(len(all_temps_list)))
        xs_p1 = list(range(len(all_p1_list)))
        xs_p2 = list(range(len(all_p2_list)))
        xs_R = list(range(len(all_R_list)))                
        xs_theta = list(range(len(all_theta_list)))
        
        sample = str(self.client.sample_time/1000)

        self.temp_ax.clear()
        self.temp_ax.plot(xs, all_temps_list, label="Temperature")
        self.temp_ax.set_title("Temperature")
        self.temp_ax.set_ylabel("Celsius")
        self.temp_ax.set_xlabel(sample + "s")

        self.pressure_ax.clear()
        self.pressure_ax.plot(xs_p1, all_p1_list, label="Pressure 1", color="blue")
        self.pressure_ax.plot(xs_p2, all_p2_list, label="Pressure 2", color="red")
        self.pressure_ax.set_title("Pressure")
        self.pressure_ax.set_ylabel("mbar")
        self.pressure_ax.set_xlabel(sample + "s")
        self.pressure_ax.legend()
        
        self.impedence_ax.clear()
        self.impedence_ax.plot(xs_R, all_R_list, label="R", color='blue')
        self.impedence_ax.plot(xs_theta, all_theta_list, label="Theta", color='red')
        self.impedence_ax.set_title("R and Theta")
        self.impedence_ax.set_xlabel(sample + "s")
        self.impedence_ax.legend()

        self.temp_canvas.draw()
        self.pressure_canvas.draw()
        self.impedence_canvas.draw()
        
   # switches valve button color and calls client valve command
    def toggle_valve_color(self, valve):
        button = self.valve_buttons[valve]
        button["fg"] = "#000000" if button["fg"] == "green" else "green"
        self.client.toggle_valve(valve)
        
    # disables set heat button, enables stop heat button, calls client set heat 
    # client command
    def toggle_set_heat(self):
        
        temp = self.set_temp_text.get()
        if not temp.isdigit() or int(temp) < 30 or int(temp) > 45:
            self.show_error("Temperature must be and integer between 30 and 45 Celsius")
        else:
            self.client.should_temp = False
            self.client.temp_to_set_to = self.set_temp_text.get()
            self.client.set_heat()
            self.set_heat_button.config(state=tk.DISABLED)
            self.stop_heat_button.config(state=tk.NORMAL)
            heat_text = f"Temp Set To: {self.client.temp_to_set_to}°C"
            self.set_temp_text.delete(0, "end")
            self.set_temp_text.insert(0, heat_text)
            self.set_temp_text.config(fg="#AAAAAA")
            self.set_heat_button.focus_set()

    # disables stop heat button, enables set heat button, calls client stop heat 
    # client command
    def toggle_stop_heat(self):
        self.client.stop_heat()
        self.client.temp_to_set_to = 0
        heat_text = f"Temp Set To: {self.client.temp_to_set_to}°C"
        self.set_temp_text.delete(0, "end")
        self.set_temp_text.insert(0, heat_text)
        self.set_temp_text.config(fg="#AAAAAA")
        
        self.stop_heat_button.config(state=tk.DISABLED)
        self.set_heat_button.config(state=tk.NORMAL)
        self.set_heat_button.focus_set()
        
    # sends pressure inputs to client
    def send_pressures(self):  
        p1 = self.set_p1_text.get()
        p2 = self.set_p2_text.get()
         
        if self.client.output_file_thread:
            self.show_error("Cannot change pressure while reading from file")
            return
        
        if p1 and p1[-3:] != "psi" and p1 != "Pressure 1":
            if self.is_valid_pressure(p1) and p1 != "":
                self.client.send_pressure1_client(float(p1))
                self.client.p1_to_set_to = p1
                p1_text = f"P1 Set To: {self.client.p1_to_set_to} psi"
                self.set_p1_text.delete(0, "end")
                self.set_p1_text.insert(0, p1_text)
                self.set_p1_text.config(fg="#AAAAAA")
                self.set_p_button.focus_set()
            else:
                self.show_error("Pressure must be between 0 and 200 psi")
            
        if p2 and p2[-3:] != "psi" and p2 != "Pressure 2":
            if self.is_valid_pressure(p2) and p2 != "":
                self.client.send_pressure2_client(float(p2))
                self.client.p2_to_set_to = p2
                p2_text = f"P2 Set To: {self.client.p2_to_set_to} psi"
                self.set_p2_text.delete(0, "end")
                self.set_p2_text.insert(0, p2_text)
                self.set_p2_text.config(fg="#AAAAAA")
                self.set_p_button.focus_set()
            else:
                self.show_error("Pressure must be between 0 and 200 psi")
          
    # returns True if pressure is between 0 - 200, False otherwise
    def is_valid_pressure(self, pressure):
        try:
            p = float(pressure)
            return 0 <= p <= 200
        except ValueError:
            return False
        
    # sets sample time
    def get_sample_time(self):
        sample_time = self.sample_time_text.get()
        if sample_time != "Seconds" and sample_time != "":
            try:
                float_value = float(sample_time)
                if float_value >= 0.1:
                    self.client.sample_time = int(float_value * 1000)
                    
                    if float_value == 1:
                        sample_text = f"Time Set To: {float_value} Second"
                    else:
                        sample_text = f"Time Set To: {float_value} Seconds"
                    
                    self.sample_time_text.delete(0, "end")
                    self.sample_time_text.insert(0, sample_text)
                    self.sample_time_text.config(fg="#AAAAAA")
                    self.set_sample_time_button.focus_set()
                else:
                    self.show_error("Sample time must be a valid float of at least 0.1")
                    return
            except ValueError:
                self.show_error("Sample time must be a valid float")
                return
        else:
            self.client.sample_time = 1000
            
    # sends command to set frequency
    def set_frequency(self):
        
        # gets value from text box
        val = self.frequency_text.get()
        
        if val.isdigit() and int(val) > 0.1 and int(val) < 100000:
            self.client.set_freq(val)
            
            # updates text box
            start_text = f"Frequency: {val} kHz"
            self.frequency_text.delete(0, "end")
            self.frequency_text.insert(0, start_text)
            self.frequency_text.config(fg="#AAAAAA")
            self.set_frequency_button.focus_set()
            return
        else:   
            self.show_error("Start frequency must be between 0.1 and 100000 Hz")
     
    # enables and disables frequency button       
    def toggle_frequency(self):
    
        if self.toggle_frequency_button.cget("text") == "Start Sweep":
            self.toggle_frequency_button.config(text="Stop Sweep")
            self.client.start_frequency()
            self.set_frequency_button.config(state=tk.NORMAL)
            start_text = "Frequency: 1000 kHz"
            self.frequency_text.delete(0, "end")
            self.frequency_text.insert(0, start_text)
            self.frequency_text.config(fg="#AAAAAA")
            self.set_frequency_button.focus_set()
            self.frequency_text.bind("<Return>", lambda event: self.set_frequency())
        else:
            self.toggle_frequency_button.config(text="Start Sweep")
            self.client.stop_frequency()
            start_text = "Frequency: 0 kHz"
            self.frequency_text.delete(0, "end")
            self.frequency_text.insert(0, start_text)
            self.frequency_text.config(fg="#AAAAAA")
            self.set_frequency_button.focus_set()
            self.set_frequency_button.config(state=tk.DISABLED)
            self.frequency_text.bind("<Return>", lambda event: self.no_return())
                    
    # if file is correctly formatted, execute button is enabled and file path
    # is stored, otherwise error message is printed
    # Correct format p1 p2 time v1 v2 v3 v4 v5 v6 v7 v8\n
    # lines with '#' will be ignored
    def scan_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            if self.client.file_formatted(file_path):
                self.execute_file_button.config(state=tk.NORMAL)
                self.input_file_label.config(text="Input: " + str(file_path))
                self.file_path = file_path
            else:
                self.show_error(
                    "File format is incorrect. Format: p1 p2 sec v1 v2 v3 v4 v5 v6 v7 v8\\n" 
                )
    
    # gets output file
    def output_file(self):
        out_file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Text Files", "*.txt")])
        
        if out_file_path:
            self.client.output_filepath = out_file_path
            self.output_file_label.config(text="Output: " + str(out_file_path))


    # disables execute button, enables stop reading button
    def execute_file(self):  
        if self.file_path:
            if self.client.file_formatted(self.file_path):          
                self.execute_file_button.config(state=tk.DISABLED)
                self.stop_reading_file_button.config(state=tk.NORMAL)
                self.start_file_thread()  
            else:
                self.show_error(
                    "File format is incorrect.\n"
                    "Correct format: p1 p2 time v1 v2 v3 v4 v5 v6 v7 v8 " 
                    "(ignores lines that begin with # | time should be non-negative integer)"
                )
         
    # returns error message for valves       
    def do_nothing(self):
        self.show_error("Cannot set valves while reading from file")
        return
    
    # returns nothing to disable buttons
    def no_return(self):
        return

    # starts file threads
    def start_file_thread(self):

        # disables valve buttons
        for button in self.valve_buttons.values():
            button.config(command=self.do_nothing)
            
        # starts file threads
        self.stop_reading_file = False
        self.client.start_file_thread(self.file_path)
        self.file_thread = threading.Thread(target=self.process_file)
        self.file_thread.start()
   
    # changes interface based on file input
    def process_file(self):
        float_value = float(self.client.sample_time) / 1000
        if float_value == 1:
            sample_text = f"Time Set To: {float_value} Second"
        else:
            sample_text = f"Time Set To: {float_value} Seconds"
        
        self.sample_time_text.delete(0, "end")
        self.sample_time_text.insert(0, sample_text)
        self.sample_time_text.config(fg="#AAAAAA")
        self.set_sample_time_button.focus_set()
        
        while not self.stop_reading_file:
            
            # changes valve button colors
            valves = self.client.current_valves
            valves = [int(valve) for valve in valves]
            valve_updates = [(i + 1, '#000000') if valve == 0 else (i + 1, 'green') for i, valve in enumerate(valves)]

            for valve, color in valve_updates:
                button = self.valve_buttons[valve]
                button.config(fg=color)
            
            valves = self.client.current_valves

            # updates pressure text
            p1_text = f"P1 Set To: {self.client.p1_to_set_to} psi"
            p2_text = f"P2 Set To: {self.client.p2_to_set_to} psi"

            self.set_p1_text.delete(0, "end")
            self.set_p1_text.insert(0, p1_text)
            self.set_p1_text.config(fg="#AAAAAA")

            self.set_p2_text.delete(0, "end")
            self.set_p2_text.insert(0, p2_text)
            self.set_p2_text.config(fg="#AAAAAA")
            
            # updates hold time label
            self.countdown_label.config(
                text=f"Hold Time: {self.client.current_sleep_time} seconds",
                fg="#FFFFFF",
            )
            
            # sleeps for client.current_sleep_time (sleep time from file)
            self.client.current_sleep_time = float(self.client.current_sleep_time)
            
            for _ in range(int(self.client.current_sleep_time)):
                if self.stop_reading_file:
                    break
                
                time.sleep(1)

            # Sleep for the remaining seconds
            time.sleep(self.client.current_sleep_time % 1)
                
    # stops file thread
    def stop_reading_file_func(self):
        
        # enables valve buttons
        for i, button in enumerate(self.valve_buttons.values(), start=1):
            button.config(command=lambda val=i: self.toggle_valve_color(val))
        
        # sets hold time to 0
        self.client.current_sleep_time = 0
        self.countdown_label.config(
                text="Hold Time: 0",
                fg="#FFFFFF",
        )
        
        # stops file threads
        self.client.stop_file_thread()
        self.stop_reading_file = True
        if self.file_thread:
            self.stop_reading_file_button.config(state=tk.DISABLED)
            self.execute_file_button.config(state=tk.NORMAL)
            self.file_thread = None 
    
    # displays current temp
    def get_current_temperature(self):
        
        # changes temp label
        self.client.update_values()
        self.temperature_label.config(
            text=f"Temperature: {self.client.current_temp}°C", 
            fg="#FFFFFF"
        )
        
        # checks if temp is too high and shows error message
        if float(self.client.current_temp) >= 55:
            self.toggle_stop_heat()
            self.show_error("Temperature reached 55°C. Heater stopped.")
                
        # calls function again after self.client.sample_time milliseconds
        self.temperature_label.after(int(self.client.sample_time), self.get_current_temperature)
        
    # displays pressures every second    
    def get_current_pressures(self):
        self.client.update_pressure()  
        p1 = self.client.current_p1
        p2 = self.client.current_p2  
        self.pressure_label.config(
            text=f"Pressure 1: {p1} psi | Pressure 2: {p2} psi",
            fg="#FFFFFF"
        )
        self.pressure_label.after(int(self.client.sample_time), self.get_current_pressures)
        
    # prints error message for one second
    def show_error(self, message):
        self.error_message.config(text=message)
        self.error_message.after(5000, lambda: self.error_message.config(text=""))
      
    # ends file threads and closes window
    def quit_program(self):
        self.stop_reading_file_func()
        self.main_window.destroy()
        exit(1)