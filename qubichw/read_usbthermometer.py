#!/usr/bin/env python3
'''
$Id: read_usbthermometer.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 17 May 2023 18:58:11 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

read and broadcast the temperature from the usb thermometer
'''
from digitemp.master import UART_Adapter
from digitemp.device import TemperatureSensor
from digitemp.exceptions import OneWireException
import time,socket
import numpy as np

# data is sent as a numpy record, to be unpacked by qubic-central
rec = np.recarray(names="STX,TIMESTAMP,VALUE",formats="uint8,float64,float32",shape=(1))
rec[0].STX = 0xAA

IP_QUBIC_CENTRAL = "192.168.2.1"
PORT = 42377
rx = (IP_QUBIC_CENTRAL,PORT)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

bus = UART_Adapter('/dev/thermometer')
try:
    roms = bus.get_connected_ROMs()
except:
    print('could not connect to USB thermometer')
    quit()
    
rom = roms[0]
sensor = TemperatureSensor(bus, rom)

while True:
    T = sensor.get_temperature()
    Tkelvin = T + 273.15
    rec[0].TIMESTAMP = np.float64(time.time())
    rec[0].VALUE = np.float32(Tkelvin)
    s.sendto(rec,rx)
    print('%.3f %7.3f' %% (rec[0].TIMESTAMP, rec[0].VALUE))
    time.sleep(0.2)


    
