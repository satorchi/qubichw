'''
$Id: frontend.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 23 Jul 2025 18:06:25 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

setup commands to the dispatcher related to setting up the bolometers
'''

def Voffset2ADU(self,Voffset):
    '''
    convert the bias offset in Volts to ADU
    taken from Qubic_Pack.dscript
    '''

    if ((Voffset >0) and (Voffset <=9)):
	ADUfloat = Voffset /2.8156e-4 - 1
    else:
	ADUfloat = 65536 + (Voffset /2.8156e-4)

    ADU = round(ADUflaot)
    return ADU

def amplitude2ADU(self,amplitude):
    '''
    convert the TES bias sine amplitude to ADU
    taken from Qubic_Pack.dscript
    '''

    if ((amplitude >0) and (amplitude <=9)):
	ADUfloat = amplitude /0.001125 - 1
    else:
	ADUfloat = 65536 + (amplitude /0.001125)
    ADU = round(ADUfloat)
    return ADU

def make_frontend_preamble(self,subsysID1,subsysID2):
    '''
    make the first bytes of a frontend command
    '''
    cmd_bytes_list = [self.SEND_TC_TO_SUBSYS_ID,
                      self.MULTINETQUICMANAGER_ID,
                      subsysID1]
    cmd_bytes_list.append( (asicNum & 0xFF0000) >> 16 )
    cmd_bytes_list.append( (asicNum & 0x00FF00) >> 8 ) 
    cmd_bytes_list.append( (asicNum & 0x0000FF) )
    cmd_bytes_list.append(0xaa)
    cmd_bytes_list.append(0x55)
    cmd_bytes_list.append(subsysID2)
    cmd_bytes_list.append(0x00)
    return cmd_bytes_list

def make_frontend_suffix(self,cmd_bytes_list):
    '''
    add the final bytes to the frontend command
    '''
    cmd_bytes_list.append(0xfa)
    cmd_bytes_list.append(0xda)
    return cmd_bytes_list

def make_command_startstopFLL(self,asicNum,onOff):
    '''
    make the command to start or stop the FLL
    '''
    cmd_bytes_list = self.make_frontend_preamble(self.MULTINETQUICMANAGER_ACTIVATEPID_ID,0x14)
    cmd_bytes_list.append( (onOff & 0xFF00) >> 8 ) 
    cmd_bytes_list.append( (onOff & 0x00FF) )
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)

    return self.make_communication_packet(cmd_bytes_list)
    
def send_startFLL(self,asicNum):
    '''
    start the bolometer feedback regulations
    '''
    cmd_bytes = self.make_command_startstopFLL(asicNum,1)
    ack = self.send_command(cmd_bytes)
    
    return ack

def send_stopFLL(self,asicNum):
    '''
    stop the bolometer feedback regulations
    '''
    cmd_bytes = self.make_command_startstopFLL(asicNum,0)
    ack = self.send_command(cmd_bytes)
    
    return ack

def make_command_TESDAC_SINUS(self,amplitude,Voffset,undersampling,increment):
    '''
    make the command to configure sine modulation on the TES bias
    '''
    amplitudeADU = self.amplitude2ADU(amplitude)
    VoffsetADU = self.Voffset2ADU(Voffset)
    cmd_bytes_list = self.make_frontend_preamble(self.MULTINETQUICMANAGER_SETTESDAC_SINUS_ID,0x42)
    cmd_bytes_list.append( ((offsetADU & 0xFF00) >> 8)) 
    cmd_bytes_list.append( ((offsetADU & 0x00FF)))
    cmd_bytes_list.append( ((amplitudeADU & 0xFF00) >> 8)) 
    cmd_bytes_list.append( ((amplitudeADU & 0x00FF)))
    cmd_bytes_list.append( ((undersampling & 0xFF00) >> 8)) 
    cmd_bytes_list.append( ((undersampling & 0x00FF)))
    cmd_bytes_list.append( ((increment & 0xFF)))
    cmd_bytes_list.append((char)0x00)
    cmd_bytes_list = self.make_frontend_suffix(cmd_bytes_list)

    return self.make_communication_packet(cmd_bytes_list)
    
