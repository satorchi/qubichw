'''
$Id: calibration_source.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
       Manuel Gonzalez <manuel.gonzalez@ib.edu.ar>

$created: Tue 03 Oct 2017 19:18:51 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

send commands to the QUBIC calibration source

see documentation in:
 Tx 263 130-170GHz User Guide.pdf
 Tx 264 190-245GHz User Guide.pdf
 VDIE Synthesizer Programming Manual.pdf
 VDI Frequency Counter User Manual 2b.pdf

 https://box.in2p3.fr/s/Yib8dsGQJQZsQxo
 https://box.in2p3.fr/s/94qiMAfpbp5RTX5
 https://box.in2p3.fr/s/pCCR7WRQf2DZerH
 https://box.in2p3.fr/s/2NfFjFNEPB6jMC3

udev rules should be setup in order to identify the calibration source

save the following in file /etc/udev/rules.d/calibration-source.rules

SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="VDIE0032", ACTION=="add", OWNER="qubic", GROUP="users", MODE="0644", SYMLINK+="calsource-HF"

SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", ATTRS{serial}=="VDIE0031", ACTION=="add", OWNER="qubic", GROUP="users", MODE="0644", SYMLINK+="calsource-LF"


'''
import os,serial
import numpy as np
import datetime as dt
from satorchipy.datefunctions import utcnow

import readline
readline.parse_and_bind('tab: complete')
readline.parse_and_bind('set editing-mode vi')

default_setting = {}
default_setting['150'] = {}
default_setting['150']['frequency']  = 150.0
default_setting['220'] = {}
default_setting['220']['frequency']  = 220.0

date_fmt = '%Y-%m-%d %H:%M:%S.%f'

class calibration_source:
    '''
    a class to communicate with the calibration sources
    '''

    def __init__(self,source=None):
        self.s = None
        self.port = None
        self.calsource = None
        self.state = None
        self.init(source=source)
        return None

    def log(self,msg):
        '''
        print messages
        '''
        fullmsg = '%s: CALSOURCE - %s' % (utcnow().strftime(date_fmt),msg)
        print(fullmsg)
        return fullmsg

    def init(self,source=None):
        '''
        setup communication to the calibration source
        '''
        self.clear_connection()

        if source is None:
            source = self.calsource
        
        if source is None:
            print('Please enter the calibration source: HF or LF')
            return None

        if source.upper()=='220':
            dev='/dev/calsource-HF'
            which_freq='High'
            self.calsource = '220'
            self.factor = 24.
        else:
            dev='/dev/calsource-LF'
            which_freq='Low'
            self.calsource = '150'
            self.factor = 12.

        
        if not os.path.exists(dev):
            self.log('ERROR! No device for the %s Frequency Calibration Source.' % which_freq)
            return None

        try:
            self.s = serial.Serial(dev,timeout=0.5)
            self.port = dev
            self.log('calsource initialized on port: %s' % self.port)
        except:
            self.log('ERROR! could not connect to the %s Frequency Calibration Source.' % which_freq)
            self.s = None
        return

    def clear_connection(self):
        '''
        clear a stale connection
        this could be called by set_Frequency()
        '''
        self.s = None
        self.port = None
        return

    def is_connected(self):
        '''
        check if the calibration source is connected
        '''

        
        if self.s is None:
            self.log('is_connected:self.s is None.  initializing.')
            self.init()
        
        if self.s is None:
            self.log('is_connected:self.s is None')
            return False

        if self.port is None:
            self.log('is_connected:self.port is None')
            return False

        if not os.path.exists(self.port):
            self.log('is_connected:self.port does not exist: %s' % self.port)
            self.clear_connection()
            return False
        
        return True

    
    def set_FreqCommand(self,f):
        '''
        make the frequency command
        this code by Manuel Gonzalez
        '''
        a=[6,70]
        for i in range(5):
            a.append(int(f))
            f=f % 1
            f*=256
        b=a[0]
        for i in a[1:]:
            b=b^i
        a.append(b)
        c = bytearray(a)
        return c

    def output_Frequency(self,response):
        '''
        interpret the result of the output from the calibration source
        this code by Manuel Gonzalez
        '''

        # make sure we have a bytearray
        if not isinstance(response,bytearray):
            response=bytearray(response)

        # interpret the result
        result = ''
        for i in response[1:]:
            result+=format(i,'08b') 
            j=1
            s=0
            for i in result:
                if(int(i)):
                    s+=2**(-j)
                j+=1
        return (s+response[0])


    def send_command(self,cmd):
        '''
        send a command to the VDI device
        '''
        if self.calsource is None:
            self.log('Please initialize the calibration source')
            return None

        if not self.is_connected():
            self.log('initializing calibration source %s' % self.calsource)
            self.init(source=self.calsource)

        if not self.is_connected():
            return None
                    
        try:
            self.s.write(cmd)
        except:
            self.log("communication error: Could not send command.")
            self.clear_connection()
            return None

        try:
            response=bytearray(self.s.read(6))
        except:
            self.log("communication error:  Could not receive response.")
            self.clear_connection()
            return None

        if len(response)==0:
            self.log("communication error:  zero length response.")
            self.clear_connection()
            return None
        
        if response[0]!=85:
            self.log("communication error:  Invalid response.")
            self.clear_connection()
            return None

        if len(response)<2:
            self.log("error: no frequency value returned.")
            self.clear_connection()
            return None
        
        of=self.output_Frequency(response[1:])
        self.log('The output frequency is %.3f GHz' % of)
        self.state = {}
        self.state['frequency'] = self.factor*of
        self.state['synthesiser_frequency'] = of
        return self.state

    def set_Frequency(self,f):
        '''
        this is a wrapper to send the frequency command.
        we add the possibility to try twice in case we lost contact with the device
        '''
        of = self.send_set_Frequency(f)
        if of is None:
            of = self.send_set_Frequency(f)

        return of
    

    def send_set_Frequency(self,f):
        '''
        set the frequency.  Note that this will send the command to the device.
        the method set_FreqCommand() only formats the command without sending
        '''
        cmd = self.set_FreqCommand(f/self.factor)
        self.state = self.send_command(cmd)
        if self.state is None: return None
        return self.state['frequency']

    def set_default_settings(self):
        '''
        set default settings
        '''
        if self.calsource == '150':
            freq = 150.0

        if self.calsource == '220':
            freq = 220.0

        of = self.set_Frequency(freq)
        return of
    
    def get_Frequency(self):
        '''
        get the synthesiser frequency
        measure the frequency counter over a period of 100ms.
        see example in VDI Frequency Counter User Manual 2b.pdf
        NOTE:  THIS DOES NOT WORK!
        '''
        cmd = bytearray([0x03, 0xFC, 0x64, 0x00, 0x9B])
        self.state = self.send_command(cmd)
        return self.state

    def status(self):
        '''
        return a status message compatible with the calsource_configuration_manager
        '''
        #state = self.get_Frequency()
        if self.state is None:
            msg = 'calsource_%s:frequency=UNKNOWN' % self.calsource
            msg += ' synthesiser_%s:frequency=UNKNOWN' % self.calsource
            return msg
    
            
        msg = 'calsource_%s:frequency=%+06fGHz' % (self.calsource,self.state['frequency'])
        msg += ' synthesiser_%s:frequency=%+06fGHz' % (self.calsource,self.state['synthesiser_frequency'])
        return msg
    
        
