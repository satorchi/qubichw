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
import os,serial,time
import numpy as np
import datetime as dt

class amplifier:
    '''
    a class to communicate with the Stanford Research Systems SR560 low noise amplifier
    '''

    def __init__(self,port=None,verbosity=2):
        '''
        initialization of the amplifier object
        '''
        self.date_fmt = '%Y-%m-%d %H:%M:%S.%f'
        self.verbosity = verbosity
        self.creation = dt.datetime.utcnow()
        self.creation_str = self.creation.strftime('%Y-%m-%d %H:%M:%S')
        self.s = None
        self.port = None
        self.state = {}
        self.state['filter mode'] = None
        self.state['filter low frequency'] = None
        self.state['filter high frequency'] = None
        self.state['coupling'] = None
        self.state['dynamic range'] = None
        self.state['gain'] = None
        self.state['invert'] = None
        
        self.init(port=port)
        self.set_default_settings()
        return None

    def log(self,msg,verbosity=0):
        '''
        log message to screen and to a file
        '''
        if verbosity > self.verbosity: return
        
        filename = 'amplifier_command.log'
        h = open(filename,'a')
        h.write('%s: %s\n' % (dt.datetime.utcnow().strftime(self.date_fmt),msg))
        h.close()
        print(msg)
        return

    def init(self,port=None):
        '''
        initialize the amplifier
        '''
        self.log('AMPLIFIER initializing',verbosity=2)
        if port is None: port = self.port
        if port is None: port = '/dev/rs232_1'

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
            self.set_listen_mode()
            return True

        except:
            self.s = None
            print('ERROR: Failed to initialize amplifier device.')
        
        return False


    def is_connected(self):
        '''
        check if the amplifier is connected
        '''
        if self.port is None:
            self.log('AMPLIFIER is_connected:self.port is None',verbosity=2)
            return False

        if not os.path.exists(self.port):
            self.log('AMPLIFIER port does not exist: %s' % self.port,verbosity=2)
            self.s = None
            return False

        if self.s is None:
            self.log('AMPLIFIER is_connected:self.s is None',verbosity=2)
            return False
        
        return True

    def send_command(self,cmd):
        '''
        send a command to the amplifier
        '''
        if not self.is_connected(): return False

        cmd_encoded = ('%s\n' % cmd).encode()
        try:
            self.s.write(cmd_encoded)
        except:
            self.log('AMPLIFIER: send_command failed: %s' % cmd)
            return False
    
        return True
    
    def set_default_settings(self):
        '''
        default settings for the amplifier
        '''
        if not self.is_connected():return False
        self.log('AMPLIFIER: set default settings',verbosity=2)
        self.set_listen_mode()
        self.set_filter_mode('12db_low_pass')
        self.set_filter_frequency(10,lowhigh='low')
        self.set_filter_frequency(0.3,lowhigh='high')
        self.set_coupling('DC')
        self.set_dynamic('low_noise')
        self.set_gain(2000)
        self.set_invert_mode('ON')
        
        # self.send_command('LALL')    # tell device to listen
        # self.send_command('FLTM 2')  # filter mode: 12dB low pass
        # self.send_command('LFRQ 5')  # low pass freq: 10Hz
        # self.send_command('HFRQ 2')  # high pass freq: 0.3Hz
        # self.send_command('CPLG 1')  # coupling: DC
        # self.send_command('DYNR 0')  # dynamic range: low noise
        # self.send_command('GAIN 10') # gain: 2000
        # self.send_command('INVT 1')  # inverted
        # self.state['filter mode'] = '12db_low_pass'
        # self.state['filter low frequency'] = 10.0
        # self.state['filter high frequency'] = 0.3
        # self.state['coupling'] = 'DC'
        # self.state['dynamic range'] = 'low_noise'
        # self.state['gain'] = 10000
        # self.state['invert'] = 'off'
        return

    def set_listen_mode(self):
        '''
        tell device to listen
        '''
        time.sleep(0.5)
        self.send_command('LALL')
        time.sleep(0.5)
        return

    def set_invert_mode(self,invert_mode):
        '''
        set the invert mode:  on or off
        '''
        if not self.is_connected():return False
        if invert_mode.upper()=='ON':
            self.send_command('INVT 1')
            self.state['invert'] = invert_mode.upper()
            return True

        self.send_command('INVT 0')
        self.state['invert'] = 'OFF'
        return True
                

    def set_filter_mode(self,filter_mode):
        '''
        set the filter mode
        valid arguments: 
          "bypass"
          "6 dB low pass"
          "12 dB low pass"
          "6 dB high pass"
          "12 dB high pass"
          "bandpass"
        '''
        if not self.is_connected():return False
        valid_args = ["bypass",
                      "6db_low_pass",
                      "12db_low_pass",
                      "6db_high_pass",
                      "12db_high_pass",
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

        self.send_command('FLTM %i' % mode_idx)
        self.state['filter mode'] = valid_args[mode_idx]
        return True
        

    def set_filter_frequency(self,frequency,lowhigh='low'):
        '''
        set the frequency limit for the low-pass or high-pass or bandpass filter
        '''
        if not self.is_connected():return False
        valid_types = ['low','high']
        lowhigh = lowhigh.lower()
        if lowhigh not in valid_types:
            print('ERROR! Invalid frequency limit: %s' % lowhigh)
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

        if lowhigh=='high':
            valid_args = valid_args[0:12]

        if frequency not in valid_args:
            print('ERROR! Invalid filter frequency requested: %s' % frequency)
            return False

        mode_idx = -1
        for idx,val in enumerate(valid_args):
            if val==frequency:
                mode_idx = idx
                break

        if lowhigh=='low':
            cmd = 'LFRQ'
        elif lowhigh=='high':
            cmd = 'HFRQ'
        else:
            return False # should never get here.
            
        self.send_command('%s %i' % (cmd,mode_idx))
        self.state['filter %s frequency' % lowhigh] = valid_args[mode_idx]
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

        self.send_command('GAIN %i' % mode_idx)
        self.state['gain'] = valid_args[mode_idx]
        self.log('AMPLIFIER gain set to %i' % self.state['gain'],verbosity=2)
        self.log('AMPLIFIER instantiated %s' % self.creation_str,verbosity=2)
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

        self.send_command('CPLG %i' % mode_idx)
        self.state['coupling'] = valid_args[mode_idx]
        return True

    
    def set_dynamic(self,dynamic):
        '''
        set the dynamic range: low noise, high, calibration
        '''
    
        if not self.is_connected():return False
        valid_args = ['low_noise','high','calibration']
        dynamic = dynamic.lower()
        
        if dynamic not in valid_args:
            print('ERROR! Invalid dynamic range requested: %s' % dynamic)
            return False

        mode_idx = -1
        for idx,val in enumerate(valid_args):
            if val==dynamic:
                mode_idx = idx
                break

        self.send_command('DYNR %i' % mode_idx)
        self.state['dynamic range'] = valid_args[mode_idx]
        return True


    def set_setting(self,setting,value):
        '''
        a generic wrapper to set a setting (called by calsource_configuration_manager)
        '''
        if not self.is_connected():
            return 'amplifier:disconnected'

        valid_settings = ['filter_mode',
                          'dynamic_range',
                          'gain',
                          'filter_low_frequency',
                          'filter_high_frequency',
                          'coupling',
                          'invert']
        setting = setting.lower()
        if setting not in valid_settings:
            return 'amplifier:INVALID_REQUEST__%s=%s' % (setting,value)

        if setting=='filter_mode':
            chk = self.set_filter_mode(value)
            if chk:
                return 'amplifier:filter_mode=%s' % self.state['filter mode'].replace(' ','_')
            return 'amplifier:filter_mode=FAILED'

        if setting=='dynamic_range':
            chk = self.set_dynamic(value)
            if chk:
                return 'amplifier:dynamic_range=%s' % self.state['dynamic range'].replace(' ','_')
            return 'amplifier:dynamic_range=FAILED'

        if setting=='gain':
            chk = self.set_gain(value)
            if chk:
                return 'amplifier:gain=%i' % self.state['gain']
            return 'amplifier:gain=FAILED'

        if setting=='filter_low_frequency':
            chk = self.set_filter_frequency(value,lowhigh='low')
            if chk:
                return 'amplifier:filter_low_frequency=%.2fHz' % self.state['filter low frequency']
            return 'amplifier:filter_low_frequency:FAILED'

        if setting=='filter_high_frequency':
            chk = self.set_filter_frequency(value,lowhigh='high')
            if chk:
                return 'amplifier:filter_high_frequency=%.2fHz' % self.state['filter high frequency']
            return 'amplifier:filter_high_frequency:FAILED'

        if setting=='coupling':
            chk = self.set_coupling(value)
            if chk:
                return 'amplifier:coupling=%s' % self.state['coupling']
            return 'amplifier:coupling:FAILED'

        if setting=='invert':
            chk = self.set_invert_mode(value)
            if chk:
                return 'amplifier:invert:%s' % self.state['invert']
            return 'amplifier:invert:FAILED'
        
        return 'amplifier:%s=NOTFOUND' % setting
    
    
    def status(self):
        '''
        show the current configuration
        '''
        msg  = 'amplifier:filter_mode=%s' % self.state['filter mode'].replace(' ','_')
        msg += ' amplifier:dynamic_range=%s' % self.state['dynamic range'].replace(' ','_')
        msg += ' amplifier:gain=%i' % self.state['gain']
        if self.state['filter low frequency'] is not None:
            msg += ' amplifier:filter_low_frequency=%.2fHz' % self.state['filter low frequency']
        if self.state['filter high frequency'] is not None:
            msg += ' amplifier:filter_high_frequency=%.2fHz' % self.state['filter high frequency']
        msg += ' amplifier:coupling=%s' % self.state['coupling']
        msg += ' amplifier:invert=%s' % self.state['invert']
        self.log('AMPLIFIER returning status message: %s' % msg,verbosity=2)
        self.log('AMPLIFIER instantiated %s' % self.creation_str,verbosity=2)
        return msg
