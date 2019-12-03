#!/usr/bin/env python3
'''
$Id: fast_mmr.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$auth: Michel Piat
$created: Fri 10 May 16:37:50 CEST 2019
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

read fast temperature data from the iMACRT
'''
import sys,socket,time
import datetime as dt

mmr_ip = '192.168.2.213'
mmr_port = 12000 + int(mmr_ip.split('.')[-1])

hlp = 'Sample fast MMR temperatures'
hlp += '\n   to specifiy channels use a comma separated list'
hlp += '\n   for example:'
hlp += '\n       fast_mmr.py 3,14,25\n'
print(hlp)
    

#interesting_channels = [5,16,27] # T
interesting_channels = [3,14,25] # R
if len(sys.argv)>1:
    ch_str_list = sys.argv[1].split(',')
    interesting_channels = []
    for ch_str in ch_str_list:
        interesting_channels.append(int(ch_str))
        
    
# setup socket connection
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
sock.settimeout(10)
sock.bind(('', 12000))


# file handles
handle = []
for ch in interesting_channels:
    handle.append(open('mmr_chan%i.dat' % ch,'a'))
    

cmd = 'MMR3GET %i' % ch
cmd_encode = cmd.encode()
counter = 0
while True:

    for idx,ch in enumerate(interesting_channels):
        try:
            res = sock.sendto(cmd_encode, (mmr_ip,mmr_port))
            ret = sock.recv(1024)
        except KeyboardInterrupt:
            print('stopped by ctrl-c')
            break

        #if idx==2: print(ret)
        val_str = ret.decode().strip()
        now = dt.datetime.utcnow()
        tstamp_str = now.strftime('%s.%f')
        handle[idx].write('%s %s\n' % (tstamp_str,val_str))
        #print('%s %s' % (tstamp_str,val_str))
        time.sleep(0.05)
    #print('\n')

    counter += 1

    
print('collected %i samples' % counter)
