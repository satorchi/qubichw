#!/usr/bin/env python3
'''
$Id: mmr_mes1.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 12 Dec 2019 10:36:10 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

run the fast acquisition mode of the iMACRT (MES1 mode)

user manuel: imacrt_1.4.pdf page 25
the data packets have the following:

1 [0:1]      unsigned char      byte id
1 [1:2]      unsigned char      channel
2 [2:4]      unsigned short     number of samples in the average
1 [4:5]      unsigned char      Index I
1 [5:6]      unsigned char      Index U
4 [6:10]     unsigned int       time (seconds)
2 [10:12]    unsigned short     time (millisec)
2 [12:14]    unsigned short     status
8 [14:22]    double             current
8 [22:30]    double             DT ADC
8 [30:38]    double             Ravg over n samples
8 [38:46]    double             sum of R^2 for n samples
8 [46:54]    double             peak-to-peak for the n samples of R
8 [54:62]    double             R conversion

'''
import sys,socket,time,struct
import datetime as dt

mmr_ip = '192.168.2.213'
mmr_port = 12000 + int(mmr_ip.split('.')[-1])


def init_socket():
    '''
    initialize the socket for iMACRT MMR
    '''

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(10)
    sock.bind(('', 12000))
    return sock

def start_mes(sock):
    '''
    send the command to begin MES1 acquisition
    '''
    
    cmd = 'MES 1'
    cmd_encode = cmd.encode()
    res = sock.sendto(cmd_encode, (mmr_ip,mmr_port))
    return res


def write_dat(filename,t,v):
    '''
    write a line of data to file
    '''
    h = open(filename,'a')
    line = '%f %e\n' % (t,v)
    h.write(line)
    h.close()
    return
    

def mes_acquisition(sock):
    '''
    run the acquisition loop for MES1 mode
    '''
    
    counter = 0
    t0 = None
    while counter<121:
        print('=== %04i ===' % counter)
        try:
            bigpack = sock.recv(3*930)
        except KeyboardInterrupt:
            print('interrupted with ctrl-c')
            return False
        except:
            print('problem receiving data packet')
            return False

        pack_bytes = len(bigpack)

        if pack_bytes < 62:
            print('no more data.  received package of %i bytes' % pack_bytes)
            return False
    
        modulo = pack_bytes % 62
    
    
        if modulo!=0: 
            print('returned %i bytes. skipping this packet.' % len(bigpack)) 
            counter += 1 
            continue

        npacks = int(pack_bytes/62)
        print('number of packets: %i' % npacks)
        ch = 0
        for ctr in range(npacks):
            ret = bigpack[ctr*62:ctr*62+62]

            ch = struct.unpack('<B',ret[1:2])[0] + 1
            
            # nsamps = struct.unpack('<H',ret[2:4])[0]
            nsecs = struct.unpack('<I',ret[6:10])[0]
            nmillisecs = struct.unpack('<H',ret[10:12])[0]
            t = nsecs + 0.001*nmillisecs
            if t0 is None:
                tstamp = float(dt.datetime.utcnow().strftime('%s.%f'))
                t0 = tstamp - t
            else:
                tstamp = t0 + t
            
                                
            val = struct.unpack('<d',ret[30:38])[0]
            
            current = struct.unpack('<d',ret[14:22])[0] 
            
            # current_rounded_down = int(1e9*current)
            filename = 'mmr_mes_ch%i.txt' % ch
            write_dat(filename,tstamp,val)
            print('%02i) t0=%16.06f t=%16.06f secs: R=%011.4f | current=%010.6f' % (ctr,t0,t,val,1e9*current))

            
        counter += 1
    return True

    
    
if __name__=='__main__':
    sock = init_socket()
    start_mes(sock)
    keepgoing = True
    while keepgoing:
        start_mes(sock)
        keepgoing = mes_acquisition(sock)        
    sock.close()
    del(sock)
    
