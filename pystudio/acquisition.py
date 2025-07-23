'''
$Id: acquisition.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 23 Jul 2025 15:32:31 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

methods for setting up, starting and stopping a data acquisition
'''
from satorchipy.datefunctions import utcnow

def make_backupsID(self):
    '''
    make a 16-bit id number for the acquisition
    '''
    backups_ID = 0xFFFF & int(utcnow().timestamp())
    backups_ID_MSB = (0xFF00 & backups_ID) >> 8
    backups_ID_LSB = (0x00FF & backups_ID)
    print('backupsID: 0x%04x = %i' % (backups_ID,backups_ID))

    return backups_ID_MSB, backups_ID_LSB

def make_command_startAcquisition(self,session_name=None,comment=None):
    '''
    make the command to start an acquisition
    
    STX  CN        SIZE                ID    DATA                                          EOT
    0x55 0x00 0x00 0x00 0x00 0x00 0xNN 0xD1  0x00 0x04 backupsID session_name 0 comment 0  0xAA
    
    '''
    if session_name is None:
        session_name = 'acquisition_launched_from_python'
    if comment is None:
        comment = 'pystudio'
        
    session_name_b = bytearray(session_name.encode())
    session_name_b.append(0) # end of string indicator for QubicStudio

    comment_b = bytearray(comment.encode())
    comment_b.append(0) # end of string indicator for QubicStudio

    self.backupsID = self.make_backupsID()
    

    # command length includes the ID, the subID, the backups ID, the session_name, and the comment
    command_length = 1 + 2 + 2 + len(session_name_b) + len(comment_b)

    cmd_bytes_list = self.make_preamble(self.INTERN_TC_ID,self.START_ACQUISITION_COMMAND,command_length)
    cmd_bytes_list.append(self.backupsID[0])
    cmd_bytes_list.append(self.backupsID[1])
    cmd_bytes_list += list(session_name_b)
    cmd_bytes_list += list(comment_b)
    cmd_bytes_list.append(0xAA) # EOT

    cmd_bytes = bytearray(cmd_bytes_list)
    return cmd_bytes

def send_startAcquisition(self,session_name=None,comment=None):
    '''
    send the command to start an acquisition
    '''
    cmd_bytes = self.make_command_startAcquisition(session_name=session_name,comment=comment)
    ack = self.send_command(cmd_bytes)
    
    return ack

def make_command_stopAcquisition(self):
    '''
    make the command to stop a running acquisition

    backupsID class variable.  It is a tuple with byte-MSB and byte-LSB
    '''

    if self.backupsID is None:
        print('ERROR! There is no running acquisition to stop.  Cannot make the stop command.')
        return 0
    
    # command length includes the ID, the subID, the backups ID
    command_length = 1 + 2 + 2

    cmd_bytes_list = self.make_preamble(self.INTERN_TC_ID,self.STOP_ACQUISITION_COMMAND,command_length)
    cmd_bytes_list.append(self.backupsID[0])
    cmd_bytes_list.append(self.backupsID[1])
    cmd_bytes_list.append(0xAA) # EOT

    cmd_bytes = bytearray(cmd_bytes_list)
    return cmd_bytes

def send_stopAcquisition(self):
    '''
    send the command to stop an acquisition
    '''

    if self.backupsID is None:
        print('ERROR! There is no running acquisition to stop.')
        return 0

    cmd_bytes = self.make_command_stopAcquisition()
    ack = self.send_command(cmd_bytes)
    self.backupsID = None
    return ack

