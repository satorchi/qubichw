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
        self.state = {}
        self.state['filter mode'] = None
        self.state['filter low frequency'] = None
        self.state['filter high frequency'] = None
        self.state['coupling'] = None
        self.state['dynamic'] = None
        self.state['gain'] = None
        
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
            print('DEBUG:AMPLIFIER is_connected:self.s is None')
            return False

        if self.port is None:
            print('DEBUG:AMPLIFIER is_connected:self.port is None')
            return False

        if not os.path.exists(self.port):
            print('DEBUG:AMPLIFIER port does not exist: %s' % self.port)
            self.s = None
            return False
        
        return True
    
    
    def set_default_settings(self):
        '''
        default settings for the amplifier
        '''
        if not self.is_connected():return False
        self.s.write('LALL\n')    # tell device to listen
        self.s.write('FLTM 1\n')  # filter mode: 6dB low pass
        self.s.write('LFRQ 6\n')  # pass freq: 30Hz
        self.s.write('CPLG 1\n')  # coupling: DC
        self.s.write('DYNR 1\n')  # dynamic range: high dynamic range
        self.s.write('GAIN 10\n') # gain: 2000
        self.state['filter mode'] = '6dB low pass'
        self.state['filter low frequency'] = 30.0
        self.state['coupling'] = 'DC'
        self.state['dynamic'] = 'high'
        self.state['gain'] = 2000
        return


    def set_filter_mode(self,filter_mode):
        '''
        set the filter mode
        valid arguments: 
          "bypass"
          "6 dB low pass"
          "12 dB low pass"
          "6 dB high pass"
          "12 dB highpass"
          "bandpass"
        '''
        if not self.is_connected():return False
        valid_args = ["bypass",
                      "6 dB low pass",
                      "12 dB low pass",
                      "6 dB high pass",
                      "12 dB highpass",
                      "bandpass"]
        filter_mode = filter_mode.lower()

        if filter_mode not in valid_args:
            print('ERROR! Invalid filter mode requested: %s' % filter_mode)
            return False

        mode_idx = -1
        for idx,val in enumerate(valid_args):
            if val==filter_mode:
                mode_idx = idx
                break

        self.s.write('FLTM %i\n' % mode_idx)
        self.state['filter mode'] = valid_args[mode_idx]
        return True
        

    def set_filter_frequency(self,frequency,type='low'):
        '''
        set the frequency limit for the low-pass or high-pass or bandpass filter
        '''
        if not self.is_connected():return False
        valid_types = ['low','high']
        type = type.lower()
        if type not in valid_types:
            print('ERROR! Invalid frequency limit: %s' % type)
            return False
        
        valid_args = [0.03,
                      0.1,
                      0.3,
                      1.0,
                      3.0,
                      10.0,
                      30.0,
                      100.0,
                      300.0,
                      1000.0,
                      3000.0,
                      10000.0,
                      30000.0,
                      100000.0,
                      300000.0,
                      1000000.0]

        if type=='high':
            valid_args = valid_args[0:12]

        if frequency not in valid_args:
            print('ERROR! Invalid filter frequency requested: %s' % frequency)
            return False

        mode_idx = -1
        for idx,val in enumerate(valid_args):
            if val==frequency:
                mode_idx = idx
                break

        if type=='low':
            cmd = 'LFRQ'
        elif type=='high':
            cmd = 'HFRQ'
        else:
            return False # should never get here.
            
        self.s.write('%s %i\n' % (cmd,mode_idx))
        self.state['filter %s frequency' % type] = valid_args[mode_idx]
        return True

    
    def set_gain(self,gain):
        '''
        set the gain
        '''
        if not self.is_connected():return False
        valid_args = [1,
                      2,
                      5,
                      10,
                      20,
                      50,
                      100,
                      200,
                      500,
                      1000,
                      2000,
                      5000,
                      10000,
                      20000,
                      50000]
        if gain not in valid_args:
            print('ERROR! Invalid gain requested: %i' % gain)
            return False

        mode_idx = -1
        for idx,val in enumerate(valid_args):
            if val==gain:
                mode_idx = idx
                break

        self.s.write('GAIN %i\n' % mode_idx)
        self.state['gain'] = valid_args[mode_idx]
        print('DEBUG:AMPLIFIER gain set to %i' % self.state['gain'])
        return True

    def set_coupling(self,coupling):
        '''
        set the coupling mode: ground, DC, AC
        '''
        if not self.is_connected():return False
        valid_args = ['GROUND','DC','AC']
        coupling = coupling.upper()
        
        if coupling not in valid_args:
            print('ERROR! Invalid coupling requested: %s' % coupling)
            return False

        mode_idx = -1
        for idx,val in enumerate(valid_args):
            if val==coupling:
                mode_idx = idx
                break

        self.s.write('CPLG %i\n' % mode_idx)
        self.state['coupling'] = valid_args[mode_idx]
        return True

    
    def set_dynamic(self,dynamic):
        '''
        set the dynamic range: low noise, high, calibration
        '''
    
        if not self.is_connected():return False
        valid_args = ['low noise','high','calibration']
        dynamic = dynamic.lower()
        
        if dynamic not in valid_args:
            print('ERROR! Invalid dynamic range requested: %s' % dynamic)
            return False

        mode_idx = -1
        for idx,val in enumerate(valid_args):
            if val==dynamic:
                mode_idx = idx
                break

        self.s.write('DYNR %i\n' % mode_idx)
        self.state['dynamic'] = valid_args[mode_idx]
        return True


    def set_setting(self,setting,value):
        '''
        a generic wrapper to set a setting (called by calsource_configuration_manager)
        '''
        if not self.is_connected():
            return 'amplifier:disconnected'

        valid_settings = ['filter_mode',
                          'dynamic',
                          'gain',
                          'low_frequency',
                          'high_frequency',
                          'coupling']
        setting = setting.lower()
        if setting not in valid_settings:
            return 'amplifier:INVALID_REQUEST__%s=%s' % (setting,value)

        if setting=='filter_mode':
            chk = self.set_filter_mode(value.replace('_',' '))
            if chk:
                return 'amplifier:filter_mode=%s' % self.state['filter mode'].replace(' ','_')
            return 'amplifier:filter_mode=FAILED'

        if setting=='dynamic':
            chk = self.set_dynamic(value)
            if chk:
                return 'amplifier:dynamic=%s' % self.state['dynamic'].replace(' ','_')
            return 'amplifier:dynamic=FAILED'

        if setting=='gain':
            chk = self.set_gain(value)
            if chk:
                return 'amplifier:gain=%i' % self.state['gain']
            return 'amplifier:gain=FAILED'

        if setting=='low_frequency':
            chk = self.set_filter_frequency(value,type='low')
            if chk:
                return 'amplifier:low_frequency=%.2fHz' % self.state['filter low frequency']
            return 'amplifier:low_frequency:FAILED'

        if setting=='high_frequency':
            chk = self.set_filter_frequency(value,type='high')
            if chk:
                return 'amplifier:high_frequency=%.2fHz' % self.state['filter high frequency']
            return 'amplifier:high_frequency:FAILED'

        if setting=='coupling':
            chk = self.set_coupling(value)
            if chk:
                return 'amplifier:coupling=%s' % self.state['coupling']
            return 'amplifier:coupling:FAILED'
            
        return 'amplifier:%s=NOTFOUND' % setting
    
    
    def status(self):
        '''
        show the current configuration
        '''
        msg  = 'amplifier:filter_mode=%s' % self.state['filter mode'].replace(' ','_')
        msg += ' amplifier:dynamic=%s' % self.state['dynamic'].replace(' ','_')
        msg += ' amplifier:gain=%i' % self.state['gain']
        if self.state['filter low frequency'] is not None:
            msg += ' amplifier:low_frequency=%.2fHz' % self.state['filter low frequency']
        if self.state['filter high frequency'] is not None:
            msg += ' amplifier:high_frequency=%.2fHz' % self.state['filter high frequency']
        msg += ' amplifier:coupling=%s' % self.state['coupling']
        print('DEBUG:AMPLIFIER returning status message: %s' % msg)
        return msg
