#!/usr/bin/env python3
'''
$Id: read_calsource.py
$auth: Manuel Gonzalez <manuel.gonzalez@ib.edu.ar>
$created: Tue 30 Apr 18:16:04 CEST 2019
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

Read data from the ADC on the Raspberry Pi, and send it via socket
'''
import board
import busio
from digitalio import DigitalInOut, Direction
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_ads1x15.ads1015 as ADS
import socket
import datetime as dt
import numpy as np
import struct

# data is sent as a numpy record, to be unpacked by QubicStudio (and others)
rec = np.recarray(names="STX,TIMESTAMP,VALUE",formats="uint8,float64,int64",shape=(1))
rec[0].STX = 0xAA

ADC_RATE = 3300
data_rate = 300.
deltat = dt.timedelta(microseconds=1e6/data_rate*0.85)

i2c = busio.I2C(board.SCL, board.SDA)

ads = ADS.ADS1015(i2c)
ads.gain = 2
ads.data_rate = ADC_RATE

chan0 = AnalogIn(ads, ADS.P0)

ads.mode = 0x0000
ads.comparator_config = 0

#IP_BROADCAST = "192.168.2.255"
IP_QUBIC_CENTRAL = "192.168.2.1"
IP_PIGPS = "192.168.2.17"
IP_QUBICSTUDIO = "192.168.2.8"

receivers = [IP_QUBICSTUDIO,
             IP_QUBIC_CENTRAL,
             IP_PIGPS]


PORT = 31337

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
date_now = dt.datetime.utcnow()
old_date = date_now
old_print_date = date_now
count = 0

while True:
    value = chan0.value
    date_now = dt.datetime.utcnow()
    if(date_now-old_date>deltat):
        sdata = date_now.strftime("%s.%f") + "\t" + str(value)
        rec[0].TIMESTAMP = np.float64(date_now.strftime("%s.%f"))
        rec[0].VALUE = np.int64(value)
        for rx in receivers:
            #s.sendto(sdata.encode(), (rx,PORT))
            s.sendto(rec,(rx,PORT))
        old_date = date_now 
        count+=1
    if(date_now-old_print_date > dt.timedelta(seconds=1)):
        t_hex_B = hex(struct.unpack('>Q',struct.pack('<d',rec[0].TIMESTAMP))[0]).upper().replace('X','x')
        t_hex_L = hex(struct.unpack('<Q',struct.pack('<d',rec[0].TIMESTAMP))[0]).upper().replace('X','x')
        
        string_to_print = "%s %s %s\tRate:% d" % (t_hex_B,t_hex_L,sdata,count)
        print(string_to_print, end='\r',flush=True)
        old_print_date = date_now
        count=0


