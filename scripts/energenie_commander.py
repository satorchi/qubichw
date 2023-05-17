#!/usr/bin/env python3
'''
$Id: energenie_commander.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 16 May 2023 08:46:51 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

switch on/off desired sockets in one of the Energenie power bar
'''
import sys
from qubichw.energenie import energenie, socketinfo

def usage():
    '''
    print a usage message
    '''
    msg = 'usage: %s <Energenie name> <on|off>' % sys.argv[0]
    msg += '\nvalid Energenie names are: 1 or 2'
    msg += '\nvalid commands are: status, on, off\n'
    print(msg)
    return None


def parseargs():
    '''
    parse the arguments.  There should be only two: device name, command
    '''
    if len(sys.argv)<3:
        return usage()

    valid_cmds = ['status','on','off']

    parms = {}
    for arg in sys.argv[1:]:
        if arg.lower() in valid_cmds:
            parms['cmd'] = arg.lower()
            continue

        for pbname in socketinfo.keys():
            for socknum in socketinfo[pbname].keys():
                if not isinstance(socket_no,int): continue
                
                devname = socketinfo[pbname][socknum]
                if devname.lower().find(arg.lower())>=0:
                    parms['name'] = pbname
                    parms['device'] = devname

    if 'name' in parms.keys()\
       and 'device' in parms.keys()\
       and 'cmd' in parms.keys():
        parms['ok'] = True
    else:
        parms['ok'] = False
    return parms


# main program
if __name__=='__main__':
    parms = parseargs()
    if not parms['ok']: 
        usage()
        quit()

    pb = energenie(parms['name'])

    if parms['cmd'] == 'on':
        print('Switching on %s' % parms['device'])
        pb.switchon(parms['device'])

    if parms['cmd'] == 'off':
        print('Switching off %s' % parms['device'])
        pb.switchoff(parms['device'])

    if parms['cmd'] == 'status':
        pb.get_status()

    
