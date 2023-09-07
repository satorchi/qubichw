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

# data is sent as a numpy record, to be unpacked by qubic-central and QubicStudio
rec = np.recarray(names="STX,timestamp,rpN,rpE,rpD,roll,yaw,pitchIMU,rollIMU,temperature,checksum",
                  formats="uint8,float64,int32,int32,int32,int32,int32,int32,int32,float32,int32",shape=(1))
fmt = '<Bdiiiiiiifi'
keys = rec.dtype.names[2:-1] # STX, timestamp, and checksum are treated separately
n_names = len(rec.dtype.names) - 1 # STX is not given by the SimpleRTK
rec[0].STX = 0xAA
packetsize = rec.nbytes # size of data packet broadcast on ethernet
chunksize = 4096 # size of ASCII chunk read from the GPS device

#IP_BROADCAST = "192.168.2.255"
IP_QUBIC_CENTRAL = "192.168.2.1"
IP_GROUNDGPS = "134.158.187.230" # testing at APC
receivers = [IP_GROUNDGPS] # testing at APC
PORT = 31337

def read_gps_chunk(chunk,sock,verbosity=0):
    '''
    read the lines of SimpleRTK info and broadcast
    '''

    lines = chunk.decode().split('\n')
    for line in lines:
        skipline = False
        if line.find('GPAPS')<0:continue
    
        data = line.split('GPAPS,')
        if len(data)<2: continue
    
        data_line = data[1]
        col = data_line.split(',')
        data_list = col[:-1] + col[-1].split('*')
        if len(data_list)<n_names:
            if verbosity>0: print('INCOMPLETE LINE %i columns: %s' % (len(data_list),data_line))
            continue

        now = dt.datetime.utcnow()
        date_str = '%s%s000' % (now.strftime('%Y%m%d'),data_list[0].strip())
        try:
            date = dt.datetime.strptime(date_str,'%Y%m%d%H%M%S.%f')
        except:
            if verbosity>0: print('DATE ERROR: %s' % date_str)
            continue

        
        rec[0].timestamp = date.timestamp()
        rec[0].checksum = eval('0x%s' % data_list[-1])
        for idx,key in enumerate(keys):
            data_idx = idx + 1
            val_str = data_list[data_idx]
            if val_str=='FFFF':
                val = 65535
            else:
                try:
                    val = eval(val_str)
                except:
                    if verbosity>0: print('ERROR DATA INTERPRETATION: %s' % (val_str))
                    skipline = True
                    continue
            
            exec('rec[0].%s = %i' % (key,val))
            
        if skipline: continue
        
        # broadcast the data
        for rx in receivers:
            sock.sendto(rec,(rx,PORT))
    return True

        


def broadcast_gps():
    '''
    read and broadcast the SimpleRTK data
    '''
    
    gpsdev = serial.Serial("/dev/gps_aps",timeout=0.1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    date_now = dt.datetime.utcnow()
    old_date = date_now
    trycount = 0

    while True:
        try:
            chunk = gpsdev.read(chunksize)        
            trycount = 0
        except KeyboardInterrupt:
            print('loop exit with ctrl-c')
            return
        except:
            trycount+=1
            if trycount>10000:
                print('ERROR! possible I/O error.')
                quit()
            time.sleep(0.1)
            continue
        status = read_gps_chunk(chunk,sock)

    return



def acquire_gps(listener=None,verbosity=0):
    '''
    read the SimpleRTK data on socket and write to file
    '''
    if listener is None: listener = receivers[0]
    
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client.settimeout(0.2)
    client.bind((listener,PORT))
    print('listening on: %s, %i' % (listener,PORT))
    h = open('calsource_orientation.dat','ab')

    packet_period = 1/8
    counter = 0
    while True:
        counter += 1
        try:
            dat = client.recv(packetsize)
            h.write(dat)
            dat_list = struct.unpack(fmt,dat)
            if verbosity>0: print(dat_list)
            time.sleep(packet_period)
        except socket.timeout:
            print('%8i: timeout error on socket' % counter)
            continue
        except KeyboardInterrupt:
            h.close()
            print('exit using ctrl-c')
            return
        except:
            if verbosity>0: print('problem reading socket')
            time.sleep(0.2)

    return

        
    
    
    
