'''
$Id: multimeter.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Mon 11 Mar 2019 08:03:12 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

send commands and read the measurement from the Agilent/Keysight volt meter

By default, this should be on device /dev/rs232 as specified in /etc/udev/rules.d/usb-rs232.rules

SUBSYSTEM=="tty", 
ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", OWNER="pi", GROUP="pi", MODE="0664", SYMLINK+="rs232"
'''
from __future__ import division, print_function
import serial,time,os,sys

class multimeter:
    '''
    class to send commands to the HP34401A multimeter
    '''

    def __init__(self,port='/dev/rs232'):
        self.s = None
        self.port = port
        return None

         

    def init(self,port=None):
        '''
        establish connection to the multimeter
        It should be connected by RS232 cable via USB adapter (serial port, usually /dev/rs232)

        '''
        if port is None: port = self.port
        if port is None: port = '/dev/rs232'

        # check of the requested device exists
        if not os.path.exists(port):
            print('Cannot connect to device.  Device does not exist: %s' % port)
            return None

        self.port = port
    
        s=serial.Serial(port=port,
                        baudrate=9600,
                        bytesize=8,
                        parity=serial.PARITY_NONE,
                        stopbits=1,
                        timeout=0.5,
                        xonxoff=True,
                        rtscts=False)

        print('Establishing communication with the multimeter on port %s' % port)
        s.write('*IDN?\n')
        id=s.readline()
        if id=='':
            print('ERROR! unable to communicate!')
            return None

        print('The device says: %s' % id)

        s.write('\n*CLS\n')
        time.sleep(0.5)
        s.write('SYST:REM\n')

        self.s=s
        return s


    def read_volt(self,show=False):
        '''
        read the voltage on the multimeter
        '''

        # no error checking
        s.write('MEAS:VOLT:DC? AUTO\n')
        ans=s.readline().strip()
        v=eval(ans)
        if show:
            print('V = %.3f V' % v)
        return v


        
            
        
    

