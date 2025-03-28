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
import serial, socket, time, struct
import datetime as dt
import numpy as np
from qubichk.utilities import get_myip, get_receiver_list
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import pyplot as plt

receivers = get_receiver_list('calbox.conf')

# data is sent as a numpy record, to be unpacked by qubic-central and QubicStudio
rec_formats = "uint8,float64,int32,int32,int32,int32,int32,float32,float32,float32,int32"
rec_formats_list = rec_formats.split(',')
fmt = '<Bdiiiiifffi'
rec = np.recarray(names="STX,timestamp,rpN,rpE,rpD,roll,yaw,pitchIMU,rollIMU,temperature,checksum",
                  formats=rec_formats,shape=(1))
keys = rec.dtype.names[2:-1] # STX, timestamp, and checksum are treated separately
n_names = len(rec.dtype.names) - 1 # STX is not given by the SimpleRTK
rec[0].STX = 0xAA
packetsize = rec.nbytes # size of data packet broadcast on ethernet
chunksize = 4096 # size of ASCII chunk read from the GPS device

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
        try:
            rec[0].checksum = eval('0x%s' % data_list[-1])
        except:
            if verbosity>0: print('CHECKSUM ERROR: %s' % data_list[-1])
            continue
        for idx,key in enumerate(keys):
            data_idx = idx + 1
            val_str = data_list[data_idx]
            if val_str=='NONE' or val_str=='FFFF':
                val = 65535
            else:
                try:
                    val = eval(val_str)
                except:
                    if verbosity>0: print('ERROR DATA INTERPRETATION: %s' % (val_str))
                    skipline = True
                    continue

            fmt_idx = idx + 2
            data_type = rec_formats_list[fmt_idx]
            if data_type.find('int')>=0:
                cmd = 'rec[0].%s = %i' % (key,val)
            else:
                cmd = 'rec[0].%s = %f' % (key,val)
            if verbosity>3: print('"%10s" %16.6f | %16s | executing: %s' % (val_str,val,data_type,cmd))
            exec(cmd)
            
        if skipline: continue
        
        # broadcast the data
        for rx in receivers:
            if verbosity==1: print('%s %s %s' % (date_str,rx,rec))
            if verbosity==2: print(line)
            if verbosity==3: print(data_list)
            else: time.sleep(0.05) # need a delay before reading GPS data again
            sock.sendto(rec,(rx,PORT))
    return True

        


def broadcast_gps(verbosity=0):
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
        status = read_gps_chunk(chunk,sock,verbosity=verbosity)

    return

def setup_plot_orientation():
    '''
    setup the plot for following the orientation angle in real time
    '''
    plt.ion()
    fig = plt.figure(figsize=(10,10))
    fig.canvas.manager.set_window_title('plt: orientation')
    ax = fig.add_subplot(111, projection='3d')
    ax.set_ylabel('North Component (m)',fontsize=12)
    ax.set_xlabel('East Component (m)',fontsize=12)
    ax.set_zlabel('Down Component (m)',fontsize=12)
    ax.set_xlim([-1, 1])
    ax.set_ylim([-1, 1])
    ax.set_zlim([-1, 1])
    ax.tick_params(axis='both',labelsize=12)

    # wait for window to appear
    plt.pause(0.5) 
    
    return ax

def plot_orientation(dat,ax,curve=None,dateobj=None,scale=None):
    '''
    plot the current orientation
    '''
    if curve is not None: curve.remove()
    if dateobj is not None: dateobj.remove()
    date = dt.datetime.utcfromtimestamp(dat[1])
    date_str = date.strftime('%Y-%m-%d %H:%M:%S.%f')
    now = dt.datetime.utcnow()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S.%f')
    delta = (now-date).total_seconds()
    date_text = 'data: %s\nnow:  %s\ndiff: %.3f seconds' % (date_str,now_str,delta)

    if scale is None:
        fixed_scale = False
        norm = np.sqrt(dat[2]**2 + dat[3]**2 + dat[4]**2)
        if norm==0.0: norm = 1.0
    else:
        fixed_scale = True
        norm = scale
        
    rpN = dat[2]/norm
    rpE = dat[3]/norm
    rpD = dat[4]/norm
    curve = ax.quiver(0 ,0, 0, rpN, rpE, rpD, lw=2)
    dateobj = ax.text(-1,-1,2,date_text,va='bottom',ha='left',fontsize=20)
    
    plt.pause(0.001)
    
    return curve,dateobj


def acquire_gps(listener=None,verbosity=0,monitor=False):
    '''
    read the SimpleRTK data on socket and write to file
    '''
    if monitor:
        ax = setup_plot_orientation()
        curve = None
        dateobj = None
    print_fmt = '%8i: 0x%X %s %10.2f %10.2f %10.2f %10.2f %10.2f %8.3f %8.3f %5.1f'
    
    if listener is None: listener = get_myip()
    print('listening on: %s, %i' % (listener,PORT))
    if listener is None:
        print('ERROR! Not a valid listening address.  Not connected to the network?')
        return None
              
    
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client.settimeout(0.2)
    client.bind((listener,PORT))
    h = open('calsource_orientation.dat','ab')

    packet_period = 1/8
    counter = 0
    while True:
        counter += 1
        try:
            dat = client.recv(packetsize)
            h.write(dat)
            h.flush()
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
                                   dat_list[5],
                                   dat_list[6],
                                   dat_list[7],
                                   dat_list[8],
                                   dat_list[9]
                                   )
                      )
            if monitor: curve,dateobj = plot_orientation(dat_list, ax, curve, dateobj)
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

        
    
    
    
