#!/usr/bin/env python3
'''
$Id: compressor_commander.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 13 Nov 2020 16:41:58 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

a script to run commands and get status on a compressor
'''
import sys
from qubichw.compressor import compressor

def usage():
    '''
    print a usage message
    '''
    msg = 'usage: %s <compressor number> <command>' % sys.argv[0]
    msg += '\nvalid compressors are: 1 or 2'
    msg += '\nvalid commands are: status, on, off, reset, log\n'
    print(msg)
    return None


def parseargs():
    '''
    parse the arguments.  There should be only two
    '''
    if len(sys.argv)<3:
        return usage()

    valid_cmds = ['status','on','off','reset','log']
    valid_compressors = ['1','2']
    cmd = None
    compressor = None
    for arg in sys.argv[1:]:
        if arg.lower() in valid_compressors:
            compressor = arg.lower()
            continue

        if arg.lower() in valid_cmds:
            cmd = arg.lower()
            continue

    retval = {}
    if compressor is None or cmd is None:
        retval['ok'] = False
    else:
        retval['ok'] = True
    retval['compressor'] = compressor
    retval['cmd'] = cmd
    return retval


# main program
if __name__=='__main__':
    parms = parseargs()
    if parms is None: 
        usage()
        quit()

    c = compressor(int(parms['compressor']))

    if parms['cmd'] == 'on':
        print('Switching on compressor %s' % parms['compressor'])
        c.on()

    if parms['cmd'] == 'off':
        print('Switching off compressor %s' % parms['compressor'])
        c.off()

    if parms['cmd'] == 'reset':
        print('Resetting compressor %s' % parms['compressor'])
        c.reset()

    info = c.status()
    if parms['cmd'] == 'log':
        print(info['log_message'])
        quit()      

    print('\nCompressor %s' % parms['compressor'])
    print(info['status_message'])
    print('\n')
    
