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
from qubichk.utilities import known_hosts, bytes2str

QS_IP = known_hosts['qubic-studio']

def interpret_communication(self,com_bytes,print_command_string=False, parameterList=None,verbose=True):
    '''
    interpret the communicated bytes
    '''
    retval = {}
    retval['ERROR'] = []

    if com_bytes is None:
        msg = 'No bytes to interpret.'
        retval['ERROR'].append(msg)
        print('ERROR! '+msg)
        return retval
    
    if verbose: print('BYTES:\n%s' % bytes2str(com_bytes).replace('0xAA 0x55','0xAA\n0x55'))
    retval['bytes'] = com_bytes
    retval['communication size'] = len(com_bytes)
    
    if com_bytes[0]!=0x55:
        msg = 'Incorrect STX: 0x%02X' % com_bytes[0]
        retval['ERROR'].append(msg)
        print('ERROR! '+msg)
        return retval

    counter = (com_bytes[1]<<8) + com_bytes[2]
    retval['counter'] = counter
    if verbose: print('COUNTER: 0x%04X = %i' % (counter,counter))

    cmd_size = (com_bytes[3]<<24) + (com_bytes[4]<<16) + (com_bytes[5]<<8) + com_bytes[6]
    retval['command size'] = cmd_size
    if verbose: print('CMD_SIZE: 0x%08X = %i' % (cmd_size,cmd_size))
    last_idx = 7 + cmd_size
    retval['last index'] = last_idx
    if verbose:
        print('TOTAL BYTES: %i' % len(com_bytes))
        print('LAST INDEX: %i' % last_idx)
    if last_idx!=(len(com_bytes)-1):
        msg = 'Given size does not match!'
        retval['ERROR'].append(msg)
        print('ERROR! '+msg)
    if last_idx>=len(com_bytes):
        msg = 'Given size is larger than the communication length: %i > %i' % (last_idx+1,len(com_bytes))
        retval['ERROR'].append(msg)
        print('ERROR! '+msg)
    else:
        if verbose: print('final byte (EOT): 0x%02X' % com_bytes[last_idx])

    cmd_id = com_bytes[7]
    retval['command ID'] = cmd_id
    if verbose: print('CMD_ID: 0x%02X' % cmd_id)

    sub_id = (com_bytes[8]<<8) + com_bytes[9]
    retval['command subID'] = sub_id
    if verbose: print('SUBCMD_ID: 0x%04X' % sub_id)

    
    cmd = bytearray(com_bytes[10:-1])
    retval['communication body'] = cmd
    if verbose: print('COMMAND: %s' % (bytes2str(cmd)))
    if print_command_string:
        cmd_str = cmd.decode('iso-8859-1')
        print('COMMAND: %s' % cmd_str)
    
    eot = com_bytes[-1]
    if eot!=0xaa:
        msg = 'Incorrect End of Transmission: 0x%02X' % eot
        retval['ERROR'].append(msg)
        print('ERROR! '+msg)
        return retval

    if parameterList is None: return retval

    idx = 7
    parameter_idx = 0
    while idx<=last_idx-4:
        val = (com_bytes[idx]<<24) + (com_bytes[idx+1]<<16) + (com_bytes[idx+2]<<8) + com_bytes[idx+3]
        phys_val = None
        if parameter_idx<len(parameterList):
            parm_name = parameterList[parameter_idx]
        else:
            parm_name = 'UNKNOWN parameter %i' % parameter_idx

        if parm_name=='QUBIC_TESDAC_Offset_ID':
            phys_val = self.ADU2Voffset(val)
        if parm_name=='QUBIC_TESDAC_Amplitude_ID':
            phys_val = self.ADU2amplitude(val)

        if phys_val is None:
            print('%32s 0x%08X = %10i' % (parm_name,val,val))
            retval[parm_name] = val
        else:
            print('%32s 0x%08X = %10i = %.2f V' % (parm_name,val,val,phys_val))
            retval[parm_name] = (val,phys_val)


        parameter_idx += 1
        idx += 4

    return retval
    

def print_acknowledgement(self,ack,comment=''):
    '''
    print to screen the acknowledgement
    '''
    msg = ' COMMUNICATION WITH DISPATCHER ACKNOWLEDGEMENT: %s ' % comment
    msg_len = len(msg) + 40
    msg = msg.center(msg_len,'v')
    print(msg)
    self.interpret_communication(ack)
    msg = ' COMMUNICATION WITH DISPATCHER ACKNOWLEDGED: %s ' % comment
    msg = msg.center(msg_len,'^')
    print(msg)

def subscribe_dispatcher(self):
    '''
    open a connection to the dispatcher
    '''
    self.dispatcher_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.dispatcher_socket.settimeout(0.6)

    try:
        self.dispatcher_socket.connect((QS_IP, self.DISPATCHER_PORT))
    except:
        print('ERROR! Could not subscribe to dispatcher.')
        self.dispatcher_socket = None
        return None
    
    try:
        ack = self.dispatcher_socket.recv(self.chunksize)
    except:
        print('ERROR!  NO ACKNOWLEDGEMENT for subscription.')
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
        print('No data')
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
        print('ERROR! Could not send to dispatcher.')
        return None
    
    print('sent %i bytes' % nbytes_sent)
    time.sleep(0.1)
    ack = self.get_data()
    if ack is None:
        print('ERROR!  No acknowledgement from dispatcher')
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
    cmd_bytes = self.make_command_request(reqNum,parameterList)

    # send the request
    ack = self.send_command(cmd_bytes)

    # then read the data
    time.sleep(0.1)
    ack = self.get_data()
    self.interpret_communication(ack,parameterList=parameterList)
    return ack


    
