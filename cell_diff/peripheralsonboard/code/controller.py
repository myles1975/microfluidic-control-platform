import tkinter as tk
from tkinter import filedialog
import argparse
from client import Client
from interface import Interface

calib_file = ''
path = ''
use_pressure = False

def ask_use_pressure():
    
    root = tk.Tk()
    
    root.title("Use Pressure Controller")
    
    def select_default():
        global calib_file, use_pressure
        calib_file = "default"
        use_pressure = True
        root.destroy()
        
    def select_new():
        global calib_file, use_pressure, path
        calib_file = "new"
        use_pressure = True
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        root.destroy()
        
    def select_old():
        global calib_file, use_pressure, path
        calib_file = "old"
        use_pressure = True
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        root.destroy()
        
    def select_no():
        global use_pressure
        use_pressure = False
        root.destroy()
    
    tk.Label(root, text="Pressure Controller Options").pack()
    tk.Button(root, text="Default", command=select_default).pack()
    tk.Button(root, text="New", command=select_new).pack()
    tk.Button(root, text="Old", command=select_old).pack()
    tk.Button(root, text="No Pressure", command=select_no).pack()
    
    root.mainloop()
    
    return use_pressure, calib_file, path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Board Controller")
    parser.add_argument("ip", type=str, help="IP address of the server")
    args = parser.parse_args()

    use_pressure, calib_file, path = ask_use_pressure()

    client = Client(args.ip, use_pressure=use_pressure, pressure_settings={calib_file:path})

    interface = Interface(client)
    
    client.close_connection()
