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

valid_cmds = ['status','on','off']

def usage():
    '''
    print a usage message
    '''
    msg = 'usage: %s <Energenie name> <%s>' % (sys.argv[0],'|'.join(valid_cmds))
    msg += '\nvalid Energenie names are: %s' % (', '.join(socketinfo.keys()))
    msg += '\nvalid commands are: %s\n' % (', '.join(valid_cmds))
    print(msg)
    return None


def parseargs():
    '''
    parse the arguments.  There should be only two: device name, command
    '''
    parms = {}
    parms['ok'] = False

    if len(sys.argv)<3:
        return parms

    for arg in sys.argv[1:]:
        if arg.lower() in valid_cmds:
            parms['cmd'] = arg.lower()
            continue

        for pbname in socketinfo.keys():
            for socknum in socketinfo[pbname].keys():
                if not isinstance(socknum,int): continue
                
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

    print('arguments list:')
    for key in parms.keys():
        print('%s: %s' % (key,parms[key]))
    print('\n')
    
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

    
