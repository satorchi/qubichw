#!/usr/bin/env python3
'''
$Id: central_command.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Sat 19 Dec 2020 21:00:17 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

listen for command sent on socket from QubicStudio
'''
import socket,sys
import datetime as dt

from qubichw.compressor import compressor

listener = '192.168.2.1' # qubic-central
port = 4100
nbytes = 2048
date_fmt = '%Y%m%d-%H%M%S.%f'

def writelog(msg):
    '''
    log message to a file
    '''
    filename = 'central_command.log'
    h=open(filename,'a')
    h.write('%s: %s\n' % (dt.datetime.utcnow().strftime(date_fmt),msg))
    h.close()
    return


def listen_for_command():
    '''
    listen for a command string arriving on socket from QubicStudio
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind((listener, port))

    print('listening on %s:%i' % (listener,port))

    now = dt.datetime.utcnow()        
    try:
        cmdstr, addr_tple = s.recvfrom(nbytes)
        rx_addr = addr_tple[0]
        rx_port = addr_tple[1]
        cmdstr_clean = ' '.join(cmdstr.decode().strip().split())
    except socket.error:
        rx_addr = 'NONE'
        rx_port = None
        cmdstr_clean = '%s SOCKET ERROR' % now.strftime('%s.%f')

    except:
        rx_addr = 'NONE'
        rx_port = None
        cmdstr_clean = '%s UNKNOWN ERROR' %  now.strftime('%s.%f')
            
        
    received_date = dt.datetime.utcnow()
    received_tstamp = eval(received_date.strftime('%s.%f'))
    if rx_port is None:
        logmsg('ERROR! %s' % cmdstr_clean)
    else:
        logmsg('received a command from %s:%i at %s: %s' % (rx_addr,rx_port,received_date.strftime(date_fmt),cmdstr_clean))

    retval = {}
    retval['timestamp'] = received_tstamp
    retval['cmd'] = cmdstr_clean
    retval['sender'] = rx_addr
    return retval


def set_compressor(compressor_num,cmd):
    '''
    switch off or on a compressor
    '''

    
    c = compressor(compressor_num)
    print('\nCompressor %i' % compressor_num)

    if cmd == 'on':
        logmsg('Switching on compressor %i' % compressor_num)
        c.on()
        return

    if cmd == 'off':
        logmsg('Switching off compressor %i' % compressor_num)
        c.off()
        return
              

    logmsg('Invalid command to compressor %i: %s' % (compressor_num,cmd))
    return

if __name__=='__main__':

    keepgoing = True
    while keepgoing:
        ret = listen_for_command()
        if ret['cmd'].upper()=='END COMMAND SEQUENCE':
            keepgoing = False
            break

        if ret['cmd'].lower()=='compressor1on':
            set_compressor(1,'on')
            continue

        if ret['cmd'].lower()=='compressor1off':
            set_compressor(1,'off')
            continue
        
        if ret['cmd'].lower()=='compressor2on':
            set_compressor(2,'on')
            continue
        
        if ret['cmd'].lower()=='compressor2off':
            set_compressor(2,'off')
            continue

        logmsg('unknown command: %s' % ret['cmd'])

              
            

    
