'''
$Id: read_MCP9808_thermometer.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 18 Feb 2025 07:52:53 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

Read and broadcast the temperatures in the calsource box

code copied from controleverything.com
# Distributed with a free-will license.
# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
# MCP9808
# This code is designed to work with the MCP9808_I2CS I2C Mini Module available from ControlEverything.com.
# https://www.controleverything.com/content/Temperature?sku=MCP9808_I2CS#tabs-0-product_tabset-2
'''

import os,socket,time,struct
if os.uname().machine.find('arm')>=0:
    import smbus
import datetime as dt
import numpy as np
from qubichk.utilities import get_myip

# 4 sensors in the calsource box
sensors = [0,1.2,4]
sensors = range(8)
nsensors = len(sensors)

# data is sent as a numpy record, to be unpacked by qubic-central and QubicStudio
rec_formats = "uint8,float64,float32,float32,float32,float32"
rec_formats_list = rec_formats.split(',')
fmt = '<Bdffff'
rec_names_list = ['STX','timestamp']
for sensor in sensors:
    rec_names_list.append('T%i' % sensor)
rec_names = ','.join(rec_names_list)
rec = np.recarray(names=rec_names, formats=rec_formats,shape=(1))
rec[0].STX = 0xAA
packetsize = rec.nbytes # size of data packet broadcast on ethernet

#IP_BROADCAST = "192.168.2.255"
IP_QUBIC_CENTRAL = "192.168.2.1"
IP_GROUNDGPS = "134.158.187.128" # testing at APC
receivers = [IP_GROUNDGPS] # testing at APC
PORT = 51337


def read_temperatures(verbosity=0):
    '''
    read the MCP9808 temperatures
    '''
    temperatures = -np.ones(nsensors,dtype=float)

    # Get I2C bus
    bus = smbus.SMBus(1)

    # MCP9808 address, 0x18(24)
    # Select configuration register, 0x01(1)
    # 0x0000(00)	Continuous conversion mode, Power-up default
    config = [0x00, 0x00]
    bus.write_i2c_block_data(0x18, 0x01, config)
    # MCP9808 address, 0x18(24)
    # Select resolution rgister, 0x08(8)
    #	0x03(03)	Resolution = +0.0625 / C
    bus.write_byte_data(0x18, 0x08, 0x03)


    # MCP9808 address, 0x18(24)
    # Read data back from 0x05(5), 2 bytes
    # Temp MSB, TEMP LSB
    base_address = 0x18
    for idx,Tidx in enumerate(sensors):
        addr = base_address + Tidx

        try:
            data = bus.read_i2c_block_data(addr, 0x05, 2)
                        
            # Convert the data to 13-bits
            Tcelsius = ((data[0] & 0x1F) * 256) + data[1]
            if Tcelsius > 4095: Tcelsius -= 8192                
            Tcelsius = Tcelsius * 0.0625
            Tkelvin = Tcelsius + 273.15
            if verbosity>0: print("T%i: %.2f K" % (Tidx,Tkelvin))

        except:
            Tkelvin = -1
        temperatures[idx] = Tkelvin
        return temperatures
                
def broadcast_temperatures(verbosity=0):
    '''
    read and broadcast the MCP9809 temperature data
    '''

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    date_now = dt.datetime.utcnow()
    date_str = date_now.strftime('%Y-%m-%d %H:%M:%S.%f')
    trycount = 0

    while True:
        try:
            temperatures = read_temperatures()        
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

        rec[0].STX = 0xAA
        rec[0].timestamp = dt.datetime.utcnow().timestamp()

        temperatures = read_temperatures()
        for idx,sensor in enumerate(sensors):
            fmt_idx = idx + 2
            data_type = rec_formats_list[fmt_idx]
            val = temperatures[idx]
            cmd = 'rec[0].T%i = %f' % (sensor,val)
            if verbosity>3: print('%16.6f | %16s | executing: %s' % (val,data_type,cmd))
            exec(cmd)
        
        # broadcast the data
        for rx in receivers:
            if verbosity>0: print('%s %s %s' % (date_str,rx,rec))
            else: time.sleep(0.05) # need a delay before reading data again
            sock.sendto(rec,(rx,PORT))

    
    return

def acquire_MCP9808_temperatures(listener=None,verbosity=0,monitor=False):
    '''
    read the MCP9808 temperature sensors on socket and write to file
    '''
    print_fmt = '%8i: 0x%X %s %10.2f %10.2f %10.2f %10.2f'
    
    if listener is None: listener = get_myip()
    print('listening on: %s, %i' % (listener,PORT))
    if listener is None:
        print('ERROR! Not a valid listening address.  Not connected to the network?')
        return None
              
    
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client.settimeout(0.2)
    client.bind((listener,PORT))
    h = open('calbox_temperatures.dat','ab')

    packet_period = 1/8
    counter = 0
    while True:
        counter += 1
        try:
            dat = client.recv(packetsize)
            h.write(dat)
            dat_list = struct.unpack(fmt,dat)
            if verbosity>0:
                date = dt.datetime.utcfromtimestamp(dat_list[1])
                date_str = date.strftime('%Y-%m-%d %H:%M:%S.%f')
                print(print_fmt % (counter,
                                   dat_list[0],
                                   date_str,
                                   dat_list[2],
                                   dat_list[3],
                                   dat_list[4],
                                   dat_list[5]
                                   )
                      )
            time.sleep(packet_period)
        except socket.timeout:
            now_str = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            print('%8i: %s timeout error on socket' % (counter,now_str))
            continue
        except KeyboardInterrupt:
            h.close()
            now_str = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            print('%8i: %s exit using ctrl-c' % (counter,now_str))
            return
        # except:
        #     if verbosity>0: print('%8i: problem reading socket' % counter)
        #     time.sleep(0.2)

    return
