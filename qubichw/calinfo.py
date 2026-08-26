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
from qubichw.calsource_configuration_manager import calsource_configuration_manager
from qubichw.cf_configuration_manager import cf_configuration_manager

def save_calsource_info(dump_dir):
    '''
    retrieve the calsource info, and save to file
    this takes time for the communication, so it's best to do it in a thread
    see start_acquisition() in pystudio/sequence.py
    '''
    cmds = ['status']

    calsrc = calsource_configuration_manager(role='bot', verbosity=0)
    calsrc.send_command(cmds)

    cf = calsource_configuration_manager(role='bot', verbosity=0)
    cf.send_command(cmds)

    calsrc_status = calsrc.listen_for_acknowledgement()
    cf_status = cf.listen_for_acknowledgement()

    calsrc_rx_timestamp = calsrc_status[0]
    calsrc_list = calsrc_status[1].decode().split()
    
    
    

    return
