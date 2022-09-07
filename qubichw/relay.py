'''
$Id: relay.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 20 May 2022 18:27:55 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

control the Numato relay for power supply
ref: Numato-16-Channel-USB Relay-Module.pdf
https://numato.com/docs/16-channel-usb-relay-module/
'''
import serial,subprocess,sys,os,re
from glob import glob
import datetime as dt

class relay:
    '''
    class to turn on/off power supplies using the Numato relay
    '''
    def  __init__(self,port=None,idVendor=0x2a19,idProduct=0x0c03,devices=None,verbosity=2):
        self.verbosity = verbosity
        self.instrument = None
        self.idVendor = idVendor
        self.idProduct = idProduct
        self.port = port # full path to port device, for example /dev/ttyACM0
        self.s = None # serial port
        
        if isinstance(devices,dict):
            self.device_address = devices
        else:
            self.device_address = {}
            self.device_address['amplifier']     = 15
            self.device_address['auxilliary']    = 14
            self.device_address['fan']           = 13
            self.device_address['calsource 150'] = 12
            self.device_address['laser']         = 11
            self.device_address['calsource 220'] = 10
            self.device_address['modulator']     =  9
            self.device_address['heater']        =  8
            

        self.default_setting = {}
        self.current_setting = {}
        for dev in self.device_address.keys():
            self.default_setting[dev] = 0
            self.current_setting[dev] = 0
        

        self.date_fmt = '%Y-%m-%d %H:%M:%S.%f'

        self.log('creating new relay object',verbosity=3)
        if not self.init_port(port=port):
            self.log('initialization unsuccessful.  No port found',verbosity=2)
            
        return None
    
    def log(self,msg,verbosity=0):
        '''
        log message to screen and to a file
        '''
        if verbosity > self.verbosity: return
        
        filename = 'relay.log'
        h = open(filename,'a')
        h.write('%s|RELAY| %s\n' % (dt.datetime.utcnow().strftime(self.date_fmt),msg))
        h.close()
        print(msg)
        return

    def init_port(self,port=None):
        '''
        establish connection to the Numato relay
        '''

        if port is None: port = self.port
        if port is None: port = self.find_port()
        if port is None: return False

        try:
            s = serial.Serial(port, 19200, timeout=1)
            self.s = s
        except:
            self.log('ERROR! Could not initialize port: %s' % port)
            return False

        self.port = port
        return True

    
    def close(self):
        '''
        close the port
        '''
        if self.s is None: return
        self.s.close()
        return
    
    def find_port(self):
        '''
        find the port where the relay is connected
        '''
        ttys = glob('/dev/ttyACM*')

        gotit = False
        for tty in ttys:
            self.log('Checking device: %s' % tty,verbosity=3)
            cmd = '/sbin/udevadm info -a %s' % tty
            proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out,err = proc.communicate()
            lines = out.decode().split('\n')
            find_str = 'ATTRS{idProduct}=="%04x"' % self.idProduct
            self.log('searching for: %s' % find_str,verbosity=3)
            for line in lines:
                if re.search(find_str,line):
                    gotit = True
                    self.port = tty
                    return tty

        if not gotit:
            self.log('ERROR! Did not find a valid device.  find_port argument: %s' % (','.join(ttys)),verbosity=2)
            return None

        print('Unreachable code')
        return None

    def send_command(self,command):
        '''
        send a command to the relay
        '''
        if self.s is None:
            self.log('Error!  no port configured',verbosity=1)
            return None

        cmd = '%s\r' % command
        self.s.write(cmd.encode())
        # read back the command to avoid filling the buffer.
        # This will be the response required for a query.  No separate read command is required.
        ans = self.s.read(1024)
        ans_str = ans.decode().replace('\n\r>','').strip()
        return ans_str
        
    
    def get_state(self):
        '''
        get the current state of the relay on/off
        '''
        ans = self.send_command('relay readall')
        if ans is None: return None
        
        lines = ans.split('\n')
        try:
            hexstr = '0x'+lines[-1].strip()
            bits = int(hexstr,16)
            self.assign_status(bits)
            return bits
        except:
            self.log('inappropriate answer to get_state: %s' % ans,verbosity=1)
            
        return ans

    def assign_status(self,bitmask):
        '''
        after a successful get_state command, assign the status to the current_setting dictionary
        '''
        for dev in self.device_address.keys():
            addr = self.device_address[dev]
            bit = 2**addr
            onoff = (bit & bitmask) >> addr
            self.current_setting[dev] = onoff
        return        

    def state(self):
        '''
        return the dictionary of the current state (on/off) of each device 
        connected to the relay
        The dictionary is updated with every call to get_state() (see above)
        '''
        statebits = self.get_state()
        return self.current_setting
    
    def print_state(self):
        '''
        print the on/off state of each relay
        '''
        bits = self.get_state()
        if isinstance(bits,str): return None
        
        onoff_str = ['OFF','ON']
        for dev in self.current_setting.keys():
            print('%s is %s' % (dev,onoff_str[self.current_setting[key]]))            
        return None

    def status(self):
        '''
        return status string compatible with calsource_configuration_manager
        '''
        bits = self.get_state()
        msg_list = []
        onoff_str = ['OFF','ON']
        for dev in self.current_setting.keys():
            dev_str = dev.replace(' ','_')
            msg_list.append('relay:%s=%s' % (dev_str,onoff_str[self.current_setting[dev]]))
        msg = ' '.join(msg_list)
        self.log('returning status message: %s' % msg,verbosity=2)
        return msg
        

    def switchon(self,devlist):
        '''
        switch on one or more devices
        '''
        
        if isinstance(devlist,str):
            if devlist.lower()=='all':
                devlist = self.device_address.keys()
            else:
                devlist = [devlist]

        # In order not to switch off something which is already on, we must read the current state
        bits = self.get_state()
        if not isinstance(bits,int): bits = 0
        
        for dev in devlist:
            if dev not in self.device_address.keys():
                self.log('unknown device: %s' % dev,verbosity=1)
                continue
            
            bits = bits | 2**self.device_address[dev]


        cmd = 'relay writeall %04x' % bits
        ans = self.send_command(cmd)
        return ans

    def switchoff(self,devlist):
        '''
        switch off one or more devices
        '''                
        if isinstance(devlist,str):
            if devlist.lower()=='all':
                return self.send_command('relay writeall 0000')
            else:
                devlist = [devlist]


        # In order not to switch off something which we want to remain on, we must read the current state
        bits = self.get_state()
        if not isinstance(bits,int): bits = 0
        
        for dev in devlist:
            if dev not in self.device_address.keys():
                self.log('unknown device: %s' % dev,verbosity=1)
                continue

            bit = 2**self.device_address[dev]
            bitmask = 0xffff ^ bit
            bits = bits & bitmask
            

        cmd = 'relay writeall %04x' % bits
        ans = self.send_command(cmd)
        return ans
            
 
