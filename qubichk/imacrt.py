'''
$Id: imacrt.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 28 Jul 2025 15:25:52 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

functions to read the iMACRT temperature system
user manuel: imacrt_1.4.pdf page 24-25

this is especially the MGC3 temperature controller for the TES bath temperature
see also in scripts directory:  mmr_mes1.py, fast_mmr.py (possibly to be updated)
'''
import socket
from qubichk.utilities import known_hosts

class iMACRT:
    def __init__(self,device='mgc'):
        self.sock = None
        
        if device.upper().find('MMR')==0:
            self.imacrtIP = known_hosts['mmr3']
        else:
            self.imacrtIP = known_hosts['mgc3']
        self.imacrt_port = 12000 + eval(self.imacrtIP.split('.')[-1])
        return
        
    def init_socket(self):
        '''
        initialize the socket for the iMACRT device
        '''

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1)
        sock.bind(('', 12000))
        self.sock = sock
        return sock

    def send_command(self,cmd,get_reply=True):
        '''
        send a command to the iMACRT device
        '''
        if self.sock is None:
            self.sock = self.init_socket()        
        
        full_cmd = cmd+'\n'
        cmd_b = full_cmd.encode()
        nbytes_sent = self.sock.sendto(cmd_b,(self.imacrtIP,self.imacrt_port))

        if not get_reply: return None
        
        try:
            ans_b = self.sock.recv(1024)
        except:
            print('ERROR! No reply from iMACRT device: %s' % self.imacrtIP)
            return None

        return ans_b.decode()
    
    def get_id(self):
        '''
        get the ID of the device
        '''
        cmd = '*IDN'
        ans = self.send_command(cmd)
        print('iMACRT Device: %s' % ans)
        return ans

    
    def get_mgc_pid(self):
        '''
        get the current status of the PID (on or off)
        '''
        cmd = 'MGC3GET 1'
        ans_str = self.send_command(cmd)
        ans = None
        try:
            ans = eval(ans_str)
        except:
            print('ERROR! MGC PID state unknown: %s' % ans_str)
            return None

        return ans

    def set_mgc_pid(self,onoff):
        '''
        set the PID to on or off (1 or 0)
        '''
        onoff_int = int(onoff)
        cmd = 'MGC3SET 1 %i' % onoff_int
        return self.send_command(cmd,get_reply=False)
        
        
    def get_mgc_setpoint(self):
        '''
        get the temperature set point for the TES bath temperature
        '''
        cmd = 'MGC3GET 2'
        ans_str = self.send_command(cmd)
        try:
            ans = eval(ans_str)
            print('MGC setpoint: %0.4f K')
        except:
            ans = ans_str
            print('MGC setpoint: %s' % ans)
            
        return ans
        
    def set_mgc_setpoint(self,setpt):
        '''
        set the temperature set point for the TES bath temperature
        '''
        cmd = 'MGC3SET 2 %f' % setpt
        return self.send_command(cmd,get_reply=False)


    

