#!/usr/bin/env python
'''
$Id: amplifier.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 26 Sep 2019 08:10:50 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

configure the amplifier in the Calibration Source setup
'''
from __future__ import division, print_function
import os,serial
import numpy as np

class amplifier:
    '''
    a class to communicate with the Stanford Research Systems SR560 low noise amplifier
    '''

    def __init__(self,port=None):
        '''
        initialization of the amplifier object
        '''
        self.s = None
        self.port = None
        self.init(port=port)
        self.set_default_settings()
        return None


    def init(self,port=None):
        '''
        initialize the amplifier
        '''
        if port is None: port = self.port
        if port is None: port = '/dev/rs232'

        # check of the requested device exists
        if not os.path.exists(port):
            print('Cannot connect to device.  Device does not exist: %s' % port)
            return False

        self.port = port

        try:
            s = serial.Serial(port=port,
                              baudrate=9600,
                              parity=serial.PARITY_NONE,
                              bytesize=8,
                              stopbits=2,
                              timeout=0.5)
            self.s = s
            return True

        except:
            self.s = None
            print('ERROR: Failed to initialize amplifier device.')
        
        return False


    def is_connected(self):
        '''
        check if the amplifier is connected
        '''
        if self.s is None:
            return False

        if self.port is None:
            return False

        if not os.path.exists(self.port):
            print('AMPLIFIER port does not exist: %s' % self.port)
            self.s = None
            return False

        
        return True
    
    
    def set_default_settings():
        if not self.is_connected():return False
        self.s.write('LALL\n')    # tell device to listen
        self.s.write('FLTM 1\n')  # filter mode: 6dB low pass
        self.s.write('LFRQ 6\n')  # pass freq: 30Hz
        self.s.write('CPLG 1\n')  # coupling: DC
        self.s.write('DYNR 1\n')  # dynamic range: high dynamic range
        self.s.write('GAIN 10\n') # gain: 2000
        return
