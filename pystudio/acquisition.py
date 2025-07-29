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
    # backups_ID = 0xFFFF & int(utcnow().timestamp())
    # override backups_ID... maybe it has to be something special?
    # backups_ID = 0xd428 # this seemed to work once 2025-07-23_12.58.09 but the logbook says it was 0xdb9d
    backups_ID = 0x0003 # in the dispatcher logbook, we see only 0x0003 or 0x00FF

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
    
    cmd_bytes_list = [self.INTERN_TC_ID,
                      (self.START_ACQUISITION_COMMAND & 0xFF00)>>8,
                      (self.START_ACQUISITION_COMMAND & 0x00FF),
                      self.backupsID[0],
                      self.backupsID[1]]
    cmd_bytes_list += list(session_name_b)
    cmd_bytes_list += list(comment_b)

    return self.make_communication_packet(cmd_bytes_list)

def send_startAcquisition(self,session_name=None,comment=None):
    '''
    send the command to start an acquisition
    '''
    cmd_bytes = self.make_command_startAcquisition(session_name=session_name,comment=comment)
    print('%s - Starting Acquisition' % utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    ack = self.send_command(cmd_bytes)
    
    return ack

def make_command_stopAcquisition(self):
    '''
    make the command to stop a running acquisition

    0x55 0x00 0x00 0x00 0x00 0x00 0x05 0xD1  0x00 0x05 backupId_MSB backupId_LSB 0xAA
    STX  CN        SIZE                ID    DATA                                EOT

    backupsID is a class variable.  It is a tuple with byte-MSB and byte-LSB
    '''

    if self.backupsID is None:
        print('ERROR! There is no running acquisition to stop.  Cannot make the stop command.')
        return 0
    
    cmd_bytes_list = [self.INTERN_TC_ID,
                      (self.STOP_ACQUISITION_COMMAND & 0xFF00)>>8,
                      (self.STOP_ACQUISITION_COMMAND & 0x00FF),
                      self.backupsID[0],
                      self.backupsID[1]]
    return self.make_communication_packet(cmd_bytes_list)

def send_stopAcquisition(self):
    '''
    send the command to stop an acquisition
    '''

    if self.backupsID is None:
        print('ERROR! There is no running acquisition to stop.')
        return 0

    cmd_bytes = self.make_command_stopAcquisition()
    print('%s - Stopping Acquisition' % utcnow().strftime('%Y-%m-%d %H:%M:%S'))
    ack = self.send_command(cmd_bytes)
    self.backupsID = None
    return ack

