'''
$Id: calinfo.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 26 Aug 2026 16:56:32 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

get/save the calibration info from the calsource box and from the carbon fibre
'''
import os
from qubichw.calsource_configuration_manager import calsource_configuration_manager
from qubichw.cf_configuration_manager import cf_configuration_manager
from qubichk.utilities import assign_dump_dir

def get_calsource_info(src='calsource'):
    '''
    get the status message from the calsource server
    '''
    cmds = ['status']
    if src.lower()=='cf' or src.lower().find('carb')>=0:
        server = cf_configuration_manager(role='bot', verbosity=0)
    else:
        server = calsource_configuration_manager(role='bot', verbosity=0)
        
    server.send_command(cmds)
    status_msg = server.listen_for_acknowledgement()
    return status_msg

def clean_status_message(status):
    '''
    strip away blank end spaces and make a clean text
    status should be a tuple of length 2
    first entry is the timestamp when the response was received
    the second entry is a byte array sent to QubicStudio, so I'm not changing it
    '''
    rx_list = [str(status[0])]
    status_list = status[1].decode().strip().split()
    full_list = rx_list + status_list
    clean_txt = ' '.join(full_list)
    return clean_txt

def parse_status_message(status_txt):
    '''
    parse the message returned from the calsource server

    status_txt is a string which is the clean version of the status message
      see cleaen_status_message() above

    the string is a space-separated list of items:
    1. timestamp when the response was received
    2. timestamp when command received
    3. timestamp when message sent
    4. list of space separated parameters of the form:  device:parameter=value
    '''
    
    info = {}
    status_list = status_txt.split()
    info['TIMESTAMP reception'] = status_list[0]
    info['TIMESTAMP command'] = eval(status_list[1])
    if len(status_list)<3: return info
    
    info['TIMESTAMP'] = eval(status_list[2])
    if len(status_list)<4: return info

    for item in status_list[3:]:
        parts = item.split(':')
        dev = parts[0]
        info[dev] = {}
        if len(parts)<2:
            info[dev]['status'] = 'UNKNOWN'
            continue
        
        parmval = parts[1].split('=')
        if len(parmval)<2:
            info[dev]['status'] = parmval
            continue
        parm = parmval[0]
        val_str = parmval[1]
        try:
            val = eval(val_str)
        except:
            val = val_str
        info[dev][parm] = val
        
    return info

def save_calsource_info(dump_dir):
    '''
    retrieve the calsource info, and save to file
    this takes time for the communication, so it's best to do it in a thread
    see start_acquisition() in pystudio/sequence.py
    '''
    dump_dir = assign_dump_dir(dump_dir)        
    dump_file = os.sep.join([dump_dir,'CALINFO.txt'])
    
    calinfo_list = []
    for src in ['calsource','cf']:
        info = get_calsource_info[src]
        info_txt = clean_status_message(info)
        calinfo_list.append(info_txt)

    txt = '\n'.join(calinfo_list) + '\n'
    h = open(dump_file,'a')
    h.write(txt)
    h.close()
    return
