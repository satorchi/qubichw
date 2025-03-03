'''
$Id: heater.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 26 Feb 2025 14:00:50 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

heater modes to effectively create slow, mid, and high heater modes by changing the duty cycle
'''
import os,sys,socket
import datetime as dt

# the numato relay for switching on/off
from qubichw.relay import relay as numato_relay
from qubichk.utilities import get_myip

PORT = 41337
LISTENER = get_myip()
timeout = 0.1
nbytes = 256

relay = numato_relay()

defined_mode = {}
defined_mode['off'] = {'duty': 0,
                        'on_duration': 0
                        }
defined_mode['slow'] = {'duty': 0.1,
                         'on_duration': 1
                         }
defined_mode['mid'] = {'duty': 0.5,
                        'on_duration': 2
                        }
defined_mode['fast'] = {'duty': 0.8,
                         'on_duration': 4
                         }
defined_mode['full'] = {'duty': 1,
                         'on_duration': 1
                         }

verbosity_threshold = 2
def log(msg,verbosity=0):
    '''
    print to screen if sufficiently verbose
    '''
    if verbosity<verbosity_threshold: return
    date_fmt = '%Y-%m-%d %H:%M:%S.%f'
    now = dt.datetime.utcnow()
    full_msg = '%s|HEATER| %s' % (dt.datetime.utcnow().strftime(date_fmt),msg)
    print(full_msg)
    return

def heateron():
    '''
    switch on the heater
    '''
    log('switching on the heater',verbosity=1)
    relay.switchon('heater')
    return

def heateroff():
    '''
    switch off the heater
    '''
    log('switching off the heater',verbosity=1)
    relay.switchoff('heater')
    return

def is_heateron():
    '''
    get the current on/off status of the heater
    '''
    relay_state = relay.state()
    onoff = relay_state['heater']
    return bool(onoff)
    

def check_for_command():
    '''
    listen for an acknowledgement string arriving on socket
    this message is called by the "commander" after sending a command
    '''

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(timeout)
    s.bind((LISTENER, PORT))

    now = dt.datetime.utcnow()

    try:
        msgbytes, addr_tple = s.recvfrom(nbytes)
    # except socket.timeout:
    #     log('no message',verbosity=3)
    #     return None
    except:
        log('unknown error listening to socket',verbosity=3)
        return None
    
    received_date = dt.datetime.utcnow()
    received_tstamp = received_date.timestamp()

    log('%s received command from %s: %s' % (received_date.strftime('%Y-%m-%d %H:%M:%S'),addr_tple[0],msgbytes.decode()))

    return interpret_command(received_tstamp, msgbytes)

def interpret_command(tstamp, cmdbytes):
    '''
    interpret the command string received on socket
    '''

    cmd_str = cmdbytes.decode()
    cmd_list = cmd_str.split()

    commandments = {}

    for command in cmd_list:
        if command.find('=')>0:
            parm_cmd_list = command.split('=')
            parm = parm_cmd_list[0]
            val_str = parm_cmd_list[1]
            try:
                val = eval(val_str)
            except:
                val = val_str

            commandments[parm] = val
            continue
    
        commandments[command] = 'execute'    
    
    return commandments

def run_command(commandments):
    '''
    run the given command: on, off, set heater mode
    return False if we want to exit the operation loop
    '''
    cmd_result = {}
    cmd_result['keepgoing'] = True

    for cmd in commandments.keys():
        if cmd=='off':
            heateroff()
            cmd_result['mode'] = 'off'
            return cmd_result

        if cmd=='quit':
            heateroff()
            cmd_result['mode'] = 'off'
            cmd_result['keepgoing'] = False
            return cmd_result

        if cmd=='on' or cmd=='full':
            heateron()
            cmd_result['mode'] = 'full'
            continue

        if cmd in defined_mode.keys():
            cmd_result['mode'] = cmd
            cmd_result['duty'] = defined_mode[cmd]['duty']
            cmd_result['on_duration'] = defined_mode[cmd]['on_duration']
            continue

        if cmd in ['duty','on_duration']:
            cmd_result[cmd] = commandments[cmd]
            cmd_result['mode'] = 'other'
            continue

        cmd_result[cmd] = 'unknown command'

    return cmd_result

def operation_loop():
    '''
    run a state machine to implement the heater modes
    '''
    keepgoing = True
    current_mode = 'off'
    new_mode = None
    last_statechange = dt.datetime.utcnow()
    duty = 0.0
    on_duration = 0.0
    off_duration = 1.0e6
    
    while keepgoing:
        try:
            cmd = check_for_command()
        except KeyboardInterrupt:
            print('loop exit with ctrl-c')
            return

        if cmd is not None:        
            cmd_result = run_command(cmd)
            keepgoing = cmd_result['keepgoing']
            if 'mode' in cmd_result.keys(): new_mode = cmd_result['mode']
            
        if not keepgoing:
            heateroff()            
            return

        if new_mode=='off':
            heateroff()
            current_mode='off'
            new_mode = None
            continue

        if new_mode=='full':
            heateron()
            current_mode='full'
            new_mode = None
            continue
        
        if new_mode is not None:
            current_mode = new_mode
            duty = cmd_result['duty']
            on_duration = cmd_result['on_duration']
            off_duration = on_duration/duty
            new_mode = None

        if current_mode=='off':
            # check that the heater is really off
            if is_heateron(): heateroff()
            continue
        
        if current_mode=='full':
            # check that the heater is really on
            if not is_heateron(): heateron()
            continue

        now = dt.datetime.utcnow()
        delta = now - last_statechange
        delta_seconds = delta.total_seconds()
        if is_heateron():
            if delta_seconds >= on_duration:
                heateroff()
                last_statechange = now
                continue
            continue
        else:
            if delta_seconds >= off_duration:
                heateron()
                last_statechange = now
                continue
            continue
        

    # we should never get this far, but just in case, switch off before exit
    heateroff()
    return
