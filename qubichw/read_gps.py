#!/usr/bin/env python3
'''
$Id: read_gps.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 31 Aug 2023 10:08:58 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

read data from the SimpleRTK GNSS giving the calsource box orientation
(adapted from read_calsource.py)

manual:  simpleRTK2B-SBC-CNRS_APC_ICD_01.pdf
         https://box.in2p3.fr/index.php/s/JZ5JKEe8iDYF5Rt

'''
import serial
import socket,time
import datetime as dt
import numpy as np
import struct

# data is sent as a numpy record, to be unpacked by QubicStudio (and others)
rec = np.recarray(names="STX,timestamp,rpN,rpE,rpD,roll,yaw,pitchIMU,rollIMU,temperature,checksum",
                  formats="uint8,int64,int,int,int,int,int,int,int,float,int",shape=(1))
rec[0].STX = 0xAA


#IP_BROADCAST = "192.168.2.255"
IP_QUBIC_CENTRAL = "192.168.2.1"
IP_GROUNDGPS = "134.158.187.230" # testing at APC
receivers = [IP_GROUNDGPS] # testing at APC
PORT = 31337

keys = ['timestamp','rpN','rpE','rpD','roll','yaw','pitchIMU','rollIMU','temperature','checksum']
gpsdata = {}
for key in keys:
    gpsdata[key] = []

def read_gps_packet(packet,sock):
    '''
    read the lines of SimpleRTK info
    '''

    lines = packet.decode().split('\n')
    for line in lines:
        if line.find('GPAPS')<0:continue
    
        data = line.split('GPAPS,')
        if len(data)<2: continue
    
        data_line = data[1]
        col = data_line.split(',')
        data_list = col[:-1] + col[-1].split('*')
        if len(data_list)<len(keys):
            print('INCOMPLETE LINE %i columns: %s' % (len(data_list),data_line))
            continue

        now = dt.datetime.utcnow()
        date_str = '%s%s000' % (now.strftime('%Y%m%d'),data_list[0].strip())
        try:
            date = dt.datetime.strptime(date_str,'%Y%m%d%H%M%S.%f')
        except:
            print('DATE ERROR: %s' % date_str)
            continue

        
        rec[0].timestamp = date.timestamp()
        rec[0].checksum = eval('0x%s' % data_list[-1])
        for idx,key in enumerate(keys):
            if key=='timestamp': continue
            if key=='checksum': continue
            if data_list[idx]=='FFFF':
                val = 65535
            else:
                val = eval(data_list[idx])
            exec('rec[0].%s = %i' % (key,val))

        # broadcast the data
        for rx in receivers:
            sock.sendto(rec,(rx,PORT))
    return

        



gpsdev = serial.Serial("/dev/gps_aps",timeout=0.1)
packetsize = 4096
deltat = dt.timedelta(seconds=1/8) # SimpleRTK is broadcasting at 8Hz

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

date_now = dt.datetime.utcnow()
old_date = date_now
old_print_date = date_now
count = 0
trycount = 0

while True:
    try:
        packet = gpsdev.read(packetsize)        
    except:
        trycount+=1
        if trycount>10000:
            print('ERROR! possible I/O error.')
            quit()
        time.sleep(0.1)
        continue
    read_gps_packet(packet,sock)



