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

def make_command_startstopFLL(self,asicNum,onOff):
    '''
    make the command to start or stop the FLL
    '''

    self.command_counter += 1
    cmd_bytes_list = []

    cmd_bytes_list.append(self.DISPATCHER_STX)
    cmd_bytes_list.append( (self.MULTINETQUICMANAGER_ID & 0xFF00) >>8)
    cmd_bytes_list.append( (self.MULTINETQUICMANAGER_ID & 0x00FF) )
    cmd_bytes_list.append(0)
    cmd_bytes_list.append(0)
    cmd_bytes_list.append(0)
    cmd_bytes_list.append(0)

    cmd_bytes_list.append(self.SEND_TC_TO_SUBSYS_ID)
    cmd_bytes_list.append(self.MULTINETQUICMANAGER_ACTIVATEPID_ID)

    command_length = 11
    cmd_bytes_list.append(command_length >> 8)
    cmd_bytes_list.append(command_length)

    cmd_bytes_list.append( (asicNum & 0xFF0000) >> 16 )
    cmd_bytes_list.append( (asicNum & 0x00FF00) >> 8 ) 
    cmd_bytes_list.append( (asicNum & 0x0000FF) )
    cmd_bytes_list.append(0xaa)
    cmd_bytes_list.append(0x55)
    cmd_bytes_list.append(0x14)
    cmd_bytes_list.append(0x00)
    cmd_bytes_list.append( (onOff & 0xFF00) >> 8 ) 
    cmd_bytes_list.append( (onOff & 0x00FF) )
    cmd_bytes_list.append(0xfa)
    cmd_bytes_list.append(0xda)

    cmd_bytes = bytearray(cmd_bytes_list)
    return cmd_bytes
    
def send_command_startFLL(self,asicNum):
    '''
    start the bolometer feedback regulations
    '''
    cmd_bytes = self.make_command_startstopFLL(asicNum,1)
    ack = self.send_command(cmd_bytes)
    
    return ack

def send_command_stopFLL(self,asicNum):
    '''
    stop the bolometer feedback regulations
    '''
    cmd_bytes = self.make_command_startstopFLL(asicNum,0)
    ack = self.send_command(cmd_bytes)
    
    return ack
    
