'''
$Id: energenie.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 03 Nov 2022 14:14:37 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

control of the Energenie USB power bar.  Code originally was in hk_verify.py
'''
import time,subprocess


# this is temporary and should be moved to it's own package
def shellcommand(cmd):
    '''
    run a shell command
    '''
    
    proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out,err = proc.communicate()
    return out.decode(),err.decode()


# the Energenie powerbar.
# Mon 25 Jan 2021 13:25:27 CET: The network Energenie is replaced by a USB Energenie
#from PyMS import PMSDevice
#energenie_cal = PMSDevice('energenie', '1')
energenie_cal_socket = {}
energenie_cal_socket[1] ='modulator'
energenie_cal_socket[2] ='calsource'
energenie_cal_socket[3] ='lamp'
energenie_cal_socket[4] ='amplifier'

# list of sockets in the Energenie powerbar on the housekeeping electronics rack
# also called the "Remote Controlled Power Bar 2" (RCPB2) in Emiliano's wiring diagram
energenie_socket = {}
energenie_socket[1] = 'horn'
energenie_socket[2] = 'heaters'
energenie_socket[3] = 'hwp'
energenie_socket[4] = 'thermos'

# Energenie socket numbers for various components (ie. reverse lookup)
energenie_socket_number = {}
energenie_socket_number['horn'] = 1
energenie_socket_number['heaters'] = 2
energenie_socket_number['hwp'] = 3
energenie_socket_number['thermos'] = 4
energenie_socket_number['modulator'] = 1
energenie_socket_number['calsource'] = 2
energenie_socket_number['lamp'] = 3
energenie_socket_number['amplifier'] = 4

def energenie_cal_get_socket_states():
    '''
    get the socket states of the Energenie powerbar powering the calsource (RCPB1)
    '''
    states = {}

    # check if we're local or remote
    out,err = shellcommand('hostname')
    if out.lower().find('pigps')>=0:
        cmd = 'sispmctl -g all'
    else:
        cmd = 'ssh pigps sispmctl -g all'
        
    out,err = shellcommand(cmd)
    find_str = '(Status of outlet [1-4]:\t)(off|on)'
    match = re.search(find_str,out)
    errmsg = 'ERROR! Could not get socket states from Energenie powerbar at the calibration source'
    if match is None:
        print(errmsg)
        return None
   
    for socket in energenie_cal_socket.keys():
        find_str = '(Status of outlet %i:\t)(off|on)' % socket
        match = re.search(find_str,out)
        if match is None:
            print('%s for socket %s' % (errmsg,energenie_cal_socket[socket]))
            status_str = 'UNKNOWN'
            states[socket] = status_str
        else:
            status_str = match.groups()[1]
            if status_str == 'on':
                status = True
            else:
                status = False
            
            states[socket] = status

    if len(states)==0: return None
    return states

def energenie_cal_set_socket_states(states):
    '''
    set the socket states of the calibration source Energenie powerbar (RCPB1)
    '''
    # check if we're local or remote
    out,err = shellcommand('hostname')
    if out.lower().find('pigps')>=0:
        sispmctl = 'sispmctl'
    else:
        sispmctl = 'ssh pigps sispmctl'

    retval = {}
    retval['ok'] = True
    errmsg_list = []
    msg_list = []
    on_cmd = '-o'
    off_cmd = '-f'
    for socket in states.keys():
        if states[socket]:
            cmd = '%s %s %i' % (sispmctl,on_cmd,socket)
        else:
            cmd = '%s %s %i' % (sispmctl,off_cmd,socket)
        print('setting energenie socket state with command: %s' % cmd)
        out,err = shellcommand(cmd)
        msg_list.append(out.strip())
        if err: errmsg_list.append(err.strip())

    retval['message'] = '\n'.join(msg_list)
    if len(errmsg_list)>0:
        retval['ok'] = False
        retval['error_message'] = '\n'.join(errmsg_list)
        
    return retval

def check_energenie_cal(verbosity=1,modulator_state=False):
    '''
    check for the status of the calsource Energenie sockets
    and switch on/off the modulator
    '''
    retval = {}
    retval['ok'] = True
    retval['error_message'] = ''
    retval['message'] = ''
    errmsg_list = []
    msg_list = []

    error_counter = 0
    max_count = 3
    states = None
    while (states is None and error_counter<max_count):
        msg = 'checking for calsource Energenie socket states'
        if verbosity>0: print(msg)
        time.sleep(3)
        states = energenie_cal_get_socket_states()
        if states is not None:
            for socket in energenie_cal_socket.keys():
                dev = energenie_cal_socket[socket]
                if socket not in states.keys():
                    msg = '%s is UNKNOWN' % dev
                elif states[socket]:
                    msg = '%s is ON' % dev
                else:
                    msg = '%s is OFF' % dev
                    if verbosity>0: print(msg)
                    msg_list.append(msg)

        else:
            error_counter += 1
            states = None
            msg = 'Could not get socket states from calsource Energenie powerbar: error count=%i' % error_counter
            if verbosity>0: print(msg)
            msg_list.append(msg)
            errmsg_list.append(msg)

    retval['states'] = states
    if states is None:
        retval['ok'] = False
    else:
        if modulator_state and not states[energenie_socket_number['modulator']]: # switch on for a ping
            states_tmp = states.copy()
            states_tmp[energenie_socket_number['modulator']] = modulator_state
            msg = 'switching on modulator for a ping'
            if verbosity>0: print(msg)
            msg_list.append(msg)

            time.sleep(5)
            info = energenie_cal_set_socket_states(states_tmp)    
            time.sleep(25)
            if not info['ok']:
                msg = 'failed to set Energenie sockets'
                if verbosity>0: print(msg)
                msg_list.append(msg)
                errmsg_list.append(msg)
                errmsg_list.append(info['error_message'])
                ok = False
                retval['ok'] = False
            msg_list.append(info['message'])

            
    if len(errmsg_list)>0: retval['error_message'] += '\n  '.join(errmsg_list)    
    retval['message'] = '\n'.join(msg_list)
    return retval
