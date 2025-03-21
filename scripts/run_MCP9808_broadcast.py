#!/usr/bin/env python3
'''
$Id: run_MCP9808_broadcast.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 18 Feb 2025 19:23:02 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

broadcast the MCP9808 temperature sensor data from the calibration box
'''
import sys
from qubichw.read_MCP9808_thermometer import MCP9808


verbosity = 0
acquisition_rate = None
broadcast_buffer = None
setpoint = None
PID_interval = None
PID_sensor = None
Kp = None
Ki = None
Kd = None
for arg in sys.argv:
    if arg.find('--verbosity=')==0:
        verbosity = eval(arg.split('=')[-1])
        continue

    if arg.find('--acquisition_rate=')==0:
        acquisition_rate = eval(arg.split('=')[-1])
        continue
    if arg.find('--broadcast_buffer=')==0:
        broadcast_buffer = eval(arg.split('=')[-1])
        continue
    if arg.find('--setpoint=')==0:
        setpoint = eval(arg.split('=')[-1])
        continue
    if arg.find('--PID_interval=')==0:
        PID_interval = eval(arg.split('=')[-1])
        continue
    if arg.find('--Kp=')==0:
        Kp = eval(arg.split('=')[-1])
        continue
    if arg.find('--Ki=')==0:
        Ki = eval(arg.split('=')[-1])
        continue
    if arg.find('--Kd=')==0:
        Kd = eval(arg.split('=')[-1])
        continue
    if arg.find('--PID_sensor=')==0:
        verbosity = arg.split('=')[-1]
        continue
    

thermometers = MCP9808(verbosity=verbosity,
                       acquisition_rate=acquisition_rate,
                       broadcast_buffer=broadcast_buffer,
                       setpoint=setpoint,
                       PID_interval=PID_interval,
                       PID_sensor=PID_sensor,
                       Kp=Kp,
                       Ki=Ki,
                       Kd=Kd
                       )
cli = thermometers.broadcast_temperatures()
