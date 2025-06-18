# microfluidic-control-platform

A Python-based full-stack microfluidic control platform for cell-culture experiments, featuring a TCP/IP client-server architecture, real-time Tkinter GUI with live data plotting, and seamless integration with custom hardware peripherals on Raspberry Pi designed at the Tufts Advanced Integrated Circuits and Systems Lab.


🚀 Project Overview

Purpose: Automate and monitor microfluidic experiments by controlling solenoid valves, heaters, thermocouples, and impedance measurement circuits mounted on a microscope-compatible PCB.

Host Hardware: Raspberry Pi running custom PCB peripherals.

Emulation: Includes a PressureEmulator for development and testing when real hardware is unavailable, as well as a RealPressureController for live experiments.

🧱 Architecture & Class Breakdown

cell_diff/
└── peripheralsonboard/
    └── code/
        ├── controller.py        # Utilities for device metadata and configuration
        ├── server_backend.py    # LoSServer: TCP/IP server executing hardware commands
        ├── client.py            # Client: manages device state, logging, and command dispatch
        └── interface.py         # Interface: Tkinter GUI for live control & visualization


controller.py

PressureEmulator & RealPressureController

Abstracts pressure control, allowing seamless switching between emulation and real hardware.

Provides metadata and validation for pressure ranges (0–200 psi).


server_backend.py

LoSServer class listens on a TCP socket, receives commands, and interfaces with hardware controllers.

Handles low-level I/O, error checking, and response formatting.


client.py

Client class orchestrates experiment flow: sends commands, polls sensors, logs data, and handles multithreading.

Supports both interactive command-line use and file-driven automation.


interface.py

Interface class builds a Tkinter GUI with:

Live plotting of temperature, pressure, and impedance (via Matplotlib).

Real-time status indicators and error dialogs.

File upload panel for batch commands.

Buttons for manual control.


Key Features

Dual-Mode Pressure Control: PressureEmulator for CI/testing, RealPressureController for in-lab use.

TCP/IP Client-Server: Robust communication layer enabling remote control and monitoring.

Real-Time Visualization: Live graphs of P1/P2 (psi), temperature (°C), and impedance (R & Θ).

File-Based Automation: Batch-execute experiments from formatted text files:

# p1 p2 time v1 v2 v3 v4 v5 v6 v7 v8
 20 30   10 1  0  1  0  0  1  1  0

Safety Failsafes: Automatic shutoff at 55°C, input validation, and user warnings.

Modular & Testable: Clear separation of concerns enables easy unit testing and CI integration.


How to Use Controller

Start the Server (on the Raspberry Pi)

python server_backend.py <PI_IP>

<PI_IP> is the Raspberry Pi’s IP address.

Run the Controller (on your CPU)

python controller.py <PI_IP>

Kill the Server (graceful shutdown)

Open a Python interpreter on your CPU:

python

Execute:

from client import Client
client = Client("<PI_IP>")
client.kill_server()


Files in This Repo

Raspberry Pi:

server_backend.py — LoSServer: receives commands from the CPU and dispatches to hardware APIs.

labonscope.py — LoS: core routines to sample and analyze board state.

eisb/ad5933.py — ad5933: driver and analyzer for the impedance-frequency board.


CPU (Host Machine):

controller.py — Entry point for command-line control.

interface.py — Interface: Tkinter GUI with live plotting and file upload.

client.py — Client: sends/receives TCP commands, logs data, supports interactive and file-driven workflows.

eis_board_class.py — Eis_Board: high-level client proxy for frequency-board commands.

pressure_controller.py — OB1_Pressure_Controller: abstraction for real or emulated pressure control.


Class Overview

Raspberry Pi Classes:

LoSServer — TCP/IP server interface

LoS — Lab-on-a-Scopesampler and analyzer

ad5933 — Impedance-frequency board controller


CPU Classes:

Interface — GUI frontend

Client — Core client orchestrator

Eis_Board — Frequency board proxy

OB1_Pressure_Controller — Pressure control abstraction

Get in touch: Myles Lopes | myles.m.lopes@gmail.com | LinkedIn: linkedin.com/in/myles-lopes-958bba25b
