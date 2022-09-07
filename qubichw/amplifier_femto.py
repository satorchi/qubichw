'''
$Id: amplifier_femto.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 05 Sep 2022 17:45:31 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

control/command of the FEMTO amplifier on the GPIO of the RaspberryPi
'''

import os,time
import RPi.GPIO as gpio
import numpy as np
import datetime as dt

class amplifier:
    '''
    a class to communicate with the FEMTO amplifier connected on the RaspberryPi GPIO
    '''

    def __init__(self,port=None,verbosity=2):
        '''
        initialization of the amplifier object
        '''
        self.date_fmt = '%Y-%m-%d %H:%M:%S.%f'
        self.verbosity = verbosity
        self.creation = dt.datetime.utcnow()
        self.creation_str = self.creation.strftime('%Y-%m-%d %H:%M:%S')
        self.state = {}
        self.state['bandwidth'] = None
        self.state['coupling'] = None
        self.state['gain'] = None

        self.default_setting = {}
        self.default_setting['gain'] = 20
        self.default_setting['bandwidth'] = 100
        self.default_setting['coupling'] = 'DC'
        
        self.init()
        self.set_default_settings()
        return None

    def log(self,msg,verbosity=0):
        '''
        log message to screen and to a file
        '''
        if verbosity > self.verbosity: return
        
        filename = 'amplifier_command.log'
        h = open(filename,'a')
        fullmsg = '%s: FEMTO - %s' % (dt.datetime.utcnow().strftime(self.date_fmt),msg) 
        h.write(fullmsg+'\n')
        h.close()
        print(fullmsg)
        return

    def init(self,port=None):
        '''
        initialize the amplifier
        '''
        self.log('initializing',verbosity=2)

        gpio.setmode(gpio.BCM)
        gpio.setup(17, gpio.IN) # overload
        gpio.setup(27,gpio.OUT) # offset input
        gpio.setup(22,gpio.OUT) # GAIN LSB
        gpio.setup(14,gpio.OUT) # GAIN MSB
        gpio.setup(15,gpio.OUT) # AC/DC
        gpio.setup(18,gpio.OUT) # bandwidth 100kHz/1kHz
        
        return True


    def is_connected(self):
        '''
        check if the amplifier is connected
        '''

        try:
            overload = gpio.input(17)
            return True
        except:
            return False
        
        return False
    
    def set_default_settings(self):
        '''
        default settings for the amplifier
        '''
        if not self.is_connected():return False
        self.log('AMPLIFIER: set default settings',verbosity=2)
        self.set_coupling(self.default_setting['coupling'])
        self.set_gain(self.default_setting['gain'])
        self.set_bandwidth(self.default_setting['bandwidth'])
        return

    def set_gain(self,gain):
        '''
        set the gain
        '''
        if not self.is_connected():return False
        valid_args = [20,
                      40,
                      60,
                      80]
        if gain not in valid_args:
            print('ERROR! Invalid gain requested: %i' % gain)
            return False

        mode_idx = valid_args.index(gain)
        pinstate = [(gpio.LOW,gpio.LOW),
                    (gpio.LOW,gpio.HIGH),
                    (gpio.HIGH,gpio.LOW),
                    (gpio.HIGH,gpio.HIGH)]
        gpio.output(14,pinstate[mode_idx][0])
        gpio.output(22,pinstate[mode_idx][1])        
        
        self.state['gain'] = valid_args[mode_idx]
        self.log('AMPLIFIER gain set to %i' % self.state['gain'],verbosity=2)
        return True

    def set_coupling(self,coupling):
        '''
        set the coupling mode: ground, DC, AC
        '''
        if not self.is_connected():return False
        valid_args = ['DC','AC']
        coupling = coupling.upper()
        
        if coupling not in valid_args:
            self.log('ERROR! Invalid coupling requested: %s' % coupling)
            return False
        mode_idx = valid_args.index(coupling)
        if coupling=='AC':
            gpio.output(15,gpio.HIGH)
        else:
            gpio.output(15,gpio.LOW)
        

        self.state['coupling'] = valid_args[mode_idx]
        return True

    def set_bandwidth(self,bw):
        '''
        set the bandwidth of the FEMTO amplifier:  100kHz or 1kHz
        '''
        if not self.is_connected():return False
        try:
            bw = int(bw)
        except:
            self.log('ERROR! Invalid bandwidth requested: %.2f' % bw)
            return False
        
        valid_args = [1,100]
        if bw not in valid_args:
            self.log('ERROR! Invalid bandwidth requested: %i' % bw)
            return False
        mode_idx = valid_args.index(bw)
        
        if bw==100:
            gpio.output(14,gpio.HIGH)
        else:
            gpio.output(14,gpio.LOW)
        

        self.state['bandwidth'] = valid_args[mode_idx]
        return True
        
    

    def set_setting(self,setting,value):
        '''
        a generic wrapper to set a setting (called by calsource_configuration_manager)
        '''
        if not self.is_connected():
            return 'amplifier:disconnected'

        valid_settings = self.default_setting.keys()
        setting = setting.lower()
        if setting not in valid_settings:
            return 'amplifier:INVALID_REQUEST__%s=%s' % (setting,value)

        if setting=='gain':
            chk = self.set_gain(value)
            if chk:
                return 'amplifier:gain=%i' % self.state['gain']
            return 'amplifier:gain=FAILED'

        if setting=='coupling':
            chk = self.set_coupling(value)
            if chk:
                return 'amplifier:coupling=%s' % self.state['coupling']
            return 'amplifier:coupling:FAILED'

        if setting=='bandwidth':
            chk = self.set_bandwidth(value)
            if chk:
                return 'amplifier:bandwidth:%s' % self.state['bandwidth']
            return 'amplifier:bandwidth:FAILED'
        
        return 'amplifier:%s=NOTFOUND' % setting
    
    
    def status(self):
        '''
        show the current configuration
        '''
        msg = ' amplifier:gain=%i' % self.state['gain']
        msg += ' amplifier:coupling=%s' % self.state['coupling']
        msg += ' amplifier:bandwidth=%i' % self.state['bandwidth']
        self.log('AMPLIFIER returning status message: %s' % msg,verbosity=2)
        self.log('AMPLIFIER instantiated %s' % self.creation_str,verbosity=2)
        return msg
