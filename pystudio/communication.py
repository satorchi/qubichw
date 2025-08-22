'''
$Id: communication.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 23 Jul 2025 15:29:12 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

general utilities for communicating with the dispatcher
'''
import socket,time
import numpy as np
from qubichk.utilities import known_hosts, bytes2str

QS_IP = known_hosts['qubic-studio']

def interpret_parameter_TM(self,parm_bytes,parm_name):
    '''
    interpret the body of the TM packet
    this is called from interpret_communication()
    '''

    values = {}
    # if the parameter is a number, it's a number for each ASIC (16 possible ASICs)
    # there's a weird reversal in byte-order if it's multibyte numbers
    val_numbers = np.array( np.frombuffer(parm_bytes,dtype=np.uint8), dtype=int)
    if len(parm_bytes)==32:
        val_numbers = np.zeros(16,dtype=int)
        for idx in range(16):
            idx_low = 2*idx
            val_numbers[idx] = parm_bytes[idx_low] + (parm_bytes[idx_low+1]<<8)
    elif len(parm_bytes)==64:
        val_numbers = np.zeros(16,dtype=int)
        for idx in range(16):
            idx_low = 4*idx
            val_numbers[idx] = parm_bytes[idx_low]\
                + (parm_bytes[idx_low+1]<<8)\
                + (parm_bytes[idx_low+2]<<16)\
                + (parm_bytes[idx_low+3]<<24)
            
    
    phys_val = None
    txt = bytes2str(parm_bytes)
    values['numbers'] = val_numbers
    values['value'] = val_numbers
    values['physical'] = phys_val
    values['text'] = txt
    values['ERROR'] = []
    
    # check if it's a string type response
    if parm_name=='DISP_LogbookFilename_ID':
        if parm_bytes[-1]!=0:
            msg = 'Incorrect end of string data: 0x%02X' % parm_bytes[-1]
            if self.verbosity>0: print('ERROR! %s' % msg)
            values['ERROR'].append(msg)
        txt_bytes = parm_bytes[:-1]
        txt = txt_bytes.decode('iso-8859-1')
        values['text'] = txt
        values['value'] = txt
        if self.verbosity>1: print('%s = %s' % (parm_name,txt))
        return values

    if parm_name=='QUBIC_TESDAC_Offset_ID':
        phys_val = self.ADU2Voffset(val_numbers)
    if parm_name=='QUBIC_TESDAC_Amplitude_ID':
        phys_val = self.ADU2amplitude(val_numbers)
    if parm_name=='QUBIC_TESDAC_Shape_ID':
        phys_val = []
        for shape_idx in val_numbers:
            phys_val.append(self.TESDAC_SHAPES[shape_idx])
    if parm_name=='QUBIC_relayStates_ID':
        phys_val = []
        for state_idx in val_numbers:
            if state_idx in self.RELAY_STATES.keys():
                phys_val.append(self.RELAY_STATES[state_idx])
            else:
                state_name = 'unknown relay state: %i' % state_idx
                phys_val.append(state_name)
        
        
        
    values['physical'] = phys_val
    if phys_val is not None: values['value'] = phys_val    
    return values

def interpret_packet(self,chunk,packet_start_idx,print_command_string=False):
    '''
    interpret an individual packet
    called in a loop from interpret_communication
    '''
    packet_info = {}
    packet_info['ERROR'] = []    

    stx = chunk[packet_start_idx]
    packet_info['start transmission'] = stx
    if stx!=self.DISPATCHER_STX:
        msg = 'Incorrect Start of Transmission: 0x%02X' % stx
        packet_info['ERROR'].append(msg)
        if self.verbosity>0: print('ERROR! '+msg)
        
    counter = (chunk[packet_start_idx+1]<<8) + chunk[packet_start_idx+2]
    packet_info['counter'] = counter
    if self.verbosity>1: print('COUNTER: 0x%04X = %i' % (counter,counter))

    pkt_size = (chunk[packet_start_idx+3]<<24) + (chunk[packet_start_idx+4]<<16) + (chunk[packet_start_idx+5]<<8) + chunk[packet_start_idx+6]
    packet_info['packet size'] = pkt_size
    if self.verbosity>1: print('PKT_SIZE: 0x%08X = %i' % (pkt_size,pkt_size))
    packet_end_idx = packet_start_idx + 7 + pkt_size
    packet_info['last index'] = packet_end_idx
    
    if packet_end_idx>=len(chunk):
        msg = 'Given size is larger than the communication length: %i > %i' % (packet_end_idx+1,len(chunk))
        packet_info['ERROR'].append(msg)
        if self.verbosity>0: print('ERROR! '+msg)
        packet_end_idx = len(chunk)-1
    
    eot = chunk[packet_end_idx]
    packet_info['end transmission'] = eot
    if self.verbosity>1: print('final byte (EOT): 0x%02X' % eot)
    if eot!=self.DISPATCHER_ETX:
        msg = 'Incorrect End of Transmission: 0x%02X' % eot
        packet_info['ERROR'].append(msg)
        if self.verbosity>0: print('ERROR! '+msg)

    packet_bytes = chunk[packet_start_idx:packet_end_idx]
    packet_info['bytes'] = packet_bytes

    dispatcher_id = chunk[packet_start_idx+7]
    body = chunk[packet_start_idx+8:packet_end_idx]
    packet_info['dispatcher ID'] = dispatcher_id
    packet_info['dispatcher name'] = 'unknown dispatcher ID'
    packet_info['command name'] = None
    packet_info['command subID'] = None
    if dispatcher_id in self.dispatcher_IDname.keys():
        TMcode = chunk[packet_start_idx+8]
        packet_info['TM code'] = TMcode
        if TMcode in self.dispatcher_IDname.keys(): # this is the wrong look up table
            TMname = self.dispatcher_IDname[TMcode]
        else:
            TMname = 'unknown TM name'
        packet_info['TM name'] = TMname
        
        packet_info['dispatcher name'] = self.dispatcher_IDname[dispatcher_id]
        body = chunk[packet_start_idx+9:packet_end_idx]
        if self.verbosity>1: 
            print('ID: 0x%02X %s' % (dispatcher_id,packet_info['dispatcher name']))
            
    if dispatcher_id in self.command_ID.keys():
        packet_info['command name'] = self.command_name[dispatcher_id]
        sub_id = (chunk[packet_start_idx+8]<<8) + chunk[packet_start_idx+9]
        packet_info['command subID'] = sub_id
        body = chunk[packet_start_idx+10:packet_end_idx]
        if self.verbosity>1:
            print('CMD_ID: 0x%02X %s' % (dispatcher_id,packet_info['command name']))
            print('SUBCMD_ID: 0x%04X' % sub_id)
        if print_command_string and self.verbosity>0:
            cmd_str = body.decode('iso-8859-1')
            print('COMMAND: %s' % cmd_str)
            
    packet_info['communication body'] = body
    if self.verbosity>1: print('BODY: %s' % (bytes2str(body)))
    return packet_info


def interpret_communication(self,chunk,print_command_string=False, parameterList=None):
    '''
    interpret the communicated bytes
    '''
    if parameterList is None:
        parameterList = list(self.parameterstable.keys())
    
    chunk_info = {}
    chunk_info['ERROR'] = []
    chunk_info['packet list'] = []

    if chunk is None or len(chunk)==0:
        msg = 'No bytes to interpret.'
        chunk_info['ERROR'].append(msg)
        if self.verbosity>0: print('ERROR! '+msg)
        return chunk_info
    
    chunk_info['bytes'] = chunk
    chunk_info['communication size'] = len(chunk)
    if self.verbosity>1:
        print('COMMUNICATION BYTES:\n%s' % bytes2str(chunk).replace('0xAA 0x55','0xAA\n0x55'))
        print('COMMUNICATION TOTAL BYTES: %i' % len(chunk))

    if chunk[0]!=self.DISPATCHER_STX:
        msg = 'Incorrect STX: 0x%02X (should be 0x%02X)' % (chunk[0],self.DISPATCHER_STX)
        chunk_info['ERROR'].append(msg)
        if self.verbosity>0: print('ERROR! '+msg)

    if chunk[-1]!=self.DISPATCHER_ETX:
        msg = 'Incorrect ETX: 0x%02X (should be 0x%02X)' % (chunk[-1],self.DISPATCHER_ETX)
        chunk_info['ERROR'].append(msg)
        if self.verbosity>0: print('ERROR! '+msg)

    if len(chunk)<7:
        msg = 'communication packet is too small: %i bytes' % len(chunk)
        chunk_info['ERROR'].append(msg)
        if self.verbosity>0: print('ERROR! '+msg)
        return chunk_info
    
    # there may be multiple packets in the given chunk
    if self.verbosity>1: print('\n'+' Looking at packets '.center(80,'*'))
    packet_start_idx = 0
    parm_idx = 0
    while packet_start_idx < len(chunk):
        packet_info = self.interpret_packet(chunk,packet_start_idx,print_command_string=print_command_string)
        packet_start_idx = packet_info['last index'] + 1
        chunk_info['packet list'].append(packet_info)
        if packet_info['dispatcher name']=='DISPATCHER_PARAM_REQUEST_TM_ID':
            if parm_idx>len(parameterList):
                parm_name = 'Unknown parameter %i' % parm_idx
            else:
                parm_name = parameterList[parm_idx]
            parm_vals = self.interpret_parameter_TM(packet_info['communication body'],parm_name)
            chunk_info[parm_name] = parm_vals
            parm_idx += 1
    return chunk_info
    

def print_acknowledgement(self,ack,comment=''):
    '''
    print to screen the acknowledgement
    '''
    if self.verbosity<1: return
    msg = ' COMMUNICATION WITH DISPATCHER ACKNOWLEDGEMENT: %s ' % comment
    msg_len = len(msg) + 40
    msg = msg.center(msg_len,'v')
    print(msg)
    self.interpret_communication(ack)
    msg = ' COMMUNICATION WITH DISPATCHER ACKNOWLEDGED: %s ' % comment
    msg = msg.center(msg_len,'^')
    print(msg)
    return

def subscribe_dispatcher(self):
    '''
    open a connection to the dispatcher
    '''
    self.dispatcher_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.dispatcher_socket.settimeout(0.6)

    try:
        self.dispatcher_socket.connect((QS_IP, self.DISPATCHER_PORT))
    except:
        if self.verbosity>0: print('ERROR! Could not subscribe to dispatcher.')
        self.dispatcher_socket = None
        return None
    
    try:
        ack = self.dispatcher_socket.recv(self.chunksize)
    except:
        if self.verbosity>0: print('ERROR!  NO ACKNOWLEDGEMENT for subscription.')
        return None
              
        
    self.print_acknowledgement(ack,'subscribe')
    
    return ack

def unsubscribe(self):
    '''
    close connection to the dispatcher
    '''
    if self.dispatcher_socket is None:
        print('Unsubscribe is not necessary: Not connected')
        return
    print('Unsubscribing')
    self.dispatcher_socket.close()
    del(self.dispatcher_socket)
    self.dispatcher_socket = None
    return

def get_data(self):
    '''
    get whatever the dispatcher is sending us
    '''
    if self.dispatcher_socket is None:
        ack = self.subscribe_dispatcher()

    if self.dispatcher_socket is None:
        return None

    try:
        ack = self.dispatcher_socket.recv(self.chunksize)
    except:
        if self.verbosity>0: print('No data')
        return None
    
    return ack
    

def send_command(self,cmd_bytes):
    '''
    send command to the QubicStudio Dispatcher
    '''

    if self.dispatcher_socket is None:
        self.dispatcher_socket = self.subscribe_dispatcher()

    try:
        nbytes_sent = self.dispatcher_socket.send(cmd_bytes)
    except:
        if self.verbosity>0: print('ERROR! Could not send to dispatcher.')
        return None
    
    if self.verbosity>1: print('sent %i bytes' % nbytes_sent)
    time.sleep(0.1)
    ack = self.get_data()
    if ack is None:
        if self.verbosity>0: print('ERROR!  No acknowledgement from dispatcher')
        return None
    
    self.print_acknowledgement(ack)
    return ack

def make_preamble(self,command_length):
    '''
    make the command preamble which is used for every command
    '''
    self.command_counter += 1

    cmd_bytes_list = [self.DISPATCHER_STX,
                      (self.command_counter & 0xFF00)>>8,
                      (self.command_counter & 0x00FF),
                      (command_length & 0xFF000000)>>24,
                      (command_length & 0x00FF0000)>>16,
                      (command_length & 0x0000FF00)>>8,
                      (command_length & 0x000000FF)]
    return cmd_bytes_list


def make_communication_packet(self,cmd_bytes_list):
    '''
    make the full communication with all the necessary protocols
    '''
    command_length = len(cmd_bytes_list)
    preamble_list = self.make_preamble(command_length)
    comms_packet_list = preamble_list + cmd_bytes_list
    comms_packet_list.append(self.DISPATCHER_ETX)
    comms_packet = bytearray(comms_packet_list)
    return comms_packet

def make_command_request(self,reqNum=None,parameterList=None):
    '''
    make the command to request the current settings

    The dispatcher permits options to select which parameters, but we will just ask for all of them

    reqNum : request number... I'm not sure what this is.

    '''
    if parameterList is None:
        parameterList = self.default_parameterList
        
    parameterCodeList = []
    for parm in parameterList:
        parameterCodeList.append(self.parameterstable[parm])
    
    parameterNum = 0xFFFFFFFF
    mode = parameterNum & self.TF_MASK # on enleve le bit TF si l'utilisateur s'amuse a le mettre !! (comment from Wilfried)
    mode = mode | self.ONE_SHOT
    sample_rate = 0 # sample rate if we are not using "one shot" (presumeably)
    if reqNum is None: reqNum = 1 # a guess
    
    cmd_bytes_list = [self.CONF_DISPATCHER_TC_ID]
    cmd_bytes_list.append(reqNum)
    cmd_bytes_list.append((len(parameterList) & 0xFF00)>>8)
    cmd_bytes_list.append( len(parameterList) & 0x00FF)
    cmd_bytes_list.append((mode & 0xFF000000)>>24)
    cmd_bytes_list.append((mode & 0x00FF0000)>>16)
    cmd_bytes_list.append((mode & 0x0000FF00)>>8 )
    cmd_bytes_list.append( mode & 0x000000FF     )
    cmd_bytes_list.append((sample_rate & 0xFF00)>>8)
    cmd_bytes_list.append( sample_rate & 0x00FF)


    for parmcode in parameterCodeList:
        cmd_bytes_list.append((parmcode & 0xFF0000) >> 16)
        cmd_bytes_list.append((parmcode & 0x00FF00) >> 8)
        cmd_bytes_list.append((parmcode & 0x0000FF))
    
    cmd_bytes = self.make_communication_packet(cmd_bytes_list)
    
    return cmd_bytes

def send_request(self,reqNum=None,parameterList=None):
    '''
    send a request to the dispatcher to return all parameters
    '''
    if parameterList is None:
        parameterList = self.default_parameterList
    cmd_bytes = self.make_command_request(reqNum,parameterList=parameterList)

    # send the request
    ack = self.send_command(cmd_bytes)
    vals = self.interpret_communication(ack,parameterList=parameterList)

    # then read the data
    time.sleep(0.1)
    ack = self.get_data()
    if ack is None:
        return vals
    
    vals = self.interpret_communication(ack,parameterList=parameterList)
    return vals


    
