'''
$Id: compressor.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 13 Nov 2020 04:29:00 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

a class to read and command the pulse tube compressors
'''
import serial,subprocess,sys,os,re
from glob import glob

psi_to_bar = 1.01325 /  14.696

class compressor:
    '''
    a class to read and command the pulse tube compressors
    '''

    def __init__(self,port=1):
        
        self.command = {}
        self.command['on']   = '$ON177CF\r\n'.encode()
        self.command['off']  = '$OFF9188\r\n'.encode()
        self.command['temperature'] = '$TEAA4B9\r\n'.encode()
        self.command['pressure'] = '$PRA95F7\r\n'.encode()
        self.command['id'] = '$ID1D629\r\n'.encode()
        self.command['status'] = '$STA3504\r\n'.encode()
        self.command['reset'] = '$RS12156\r\n'.encode()
        
        self.statusbits = {}
        self.statusbits[8] = 'Solonoid'
        self.statusbits[7] = 'Pressure alarm'
        self.statusbits[6] = 'Oil Level alarm'
        self.statusbits[5] = 'Water Flow alarm'
        self.statusbits[4] = 'Water Temperature alarm'
        self.statusbits[3] = 'Helium Temperature alarm'
        self.statusbits[2] = 'Phase Sequence/Fuse alarm'
        self.statusbits[1] = 'Motor Temperature alarm'
        self.statusbits[0] = 'System ON'


        self.ttyID = ['FT4PIASF','FT4PFIW1']
        self.initialized = False
        self.port = self.find_port(port)
        if self.port is not None:
            self.ser = self.init_port()

        return
    
    def find_port(self,port=1):
        '''
        find the ports where the compressors are connected
        '''
        id = None            
        ttys = glob('/dev/ttyUSB*')
        if (port==1):
            id = self.ttyID[0]
        elif (port==2):
            id = self.ttyID[1]
        elif not os.path.exists(port):
            print('ERROR!  Device does not exist: %s' % port)
            return None
        else:
            ttys = [port]


        gotit = False
        for tty in ttys:
            cmd = '/sbin/udevadm info -a %s' % tty
            proc = subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out,err = proc.communicate()
            lines = out.decode().split('\n')
            for line in lines:
                if id is not None:
                    find_str = 'ATTRS{serial}=="%s"' % id
                else:
                    find_str = 'SUBSYSTEMS==".*serial"'
                if re.search(find_str,line):
                    gotit = True
                    return tty

        if not gotit:
            print('ERROR! Did not find a valid device.  find_port argument: %s' % port)
            return None

        print('Unreachable code')
        return port
                    

    def init_port(self):
        '''
        initialize the serial port
        '''
        if self.port is None: self.port = self.find_port()
        if self.port is None: return None

        s = None
        try:
            s = serial.Serial(port=self.port,
                              baudrate=9600,
                              bytesize=8,
                              parity='N',
                              stopbits=1,
                              timeout=0.5)
        
            self.ser = s
            self.initialized = True
        except:
            self.initialized = False
        return s

    def ok(self):
        '''
        verify port status
        '''
        if not self.initialized: return False
        if self.port is None: return False
        return True
    
    def status(self):
        '''
        return the status of the compressors
        '''
        retval = {}
        retval['status'] = True
        retval['msg'] = 'ok'

        if not self.ok():
            retval['status'] = False
            retval['msg'] = 'ERROR!  Device not configured.'
            return retval
        
        cmdkey = 'id'        
        self.ser.write(self.command[cmdkey])
        ans = self.ser.readline()
        try:
            ans_decoded = ans.decode()
        except:
            ans_decoded = ans.decode('iso-8859-1')
        val = ans_decoded.strip().split(',')
        if len(val)!=5:
            retval['status'] = False
            retval['msg'] = 'ERROR! Invalid ID response from device.'
            return retval

        try:
            op_hours = float(val[2])
            retval['operating hours'] = op_hours
        except:
            retval['status'] = False
            retval['msg'] = 'ERROR! Could not read operating hours'
            return retval

        cmdkey = 'temperature'
        self.ser.write(self.command[cmdkey])
        ans = self.ser.readline()
        val = ans.decode().strip().split(',')
        if len(val)!=6:
            retval['status'] = False
            retval['msg'] = 'ERROR! Invalid temperature response from device.'
            return retval

        try:
            retval['Compressor capsule helium discharge temperature'] = float(val[1])
            retval['Water outlet temperature'] = float(val[2])
            retval['Water inlet temperature'] = float(val[3])
        except:
            retval['status'] = False
            retval['msg'] = 'ERROR! Could not read temperatures'
            return retval
        
        cmdkey = 'pressure'
        self.ser.write(self.command[cmdkey])
        ans = self.ser.readline()
        val = ans.decode().strip().split(',')
        
        if len(val)!=4:
            retval['status'] = False
            retval['msg'] = 'ERROR! Invalid pressure response from device.'
            return retval

        try:
            retval['pressure'] = '%.04fbar (relative to ambient)' % (float(val[1]) * psi_to_bar)
        except:
            retval['status'] = False
            retval['msg'] = 'ERROR! Could not read pressure'
            return retval

        cmdkey = 'status'
        self.ser.write(self.command[cmdkey])
        ans = self.ser.readline()
        val = ans.decode().strip().split(',')

        if len(val)!=3:
            retval['status'] = False
            retval['msg'] = 'ERROR! Invalid status response from device'
            return retval

        try:
            statbits = int(val[1],16)
        except:
            retval['status'] = False
            retval['msg'] = 'ERROR! Could not read status bits'
            return retval
        

        errmsg_list = []
        for bit in self.statusbits.keys():
            bitstatus = (statbits & 2**bit) > 0
            key = self.statusbits[bit]
            retval[key] = bitstatus
            if key.find('alarm')>0 and bitstatus:
                retval['status'] = False
                errmsg_list.append('ERROR! %s' % key)
            if (key=='Solonoid' or key=='System ON') and not bitstatus:
                retval['status'] = False
                errmsg_list.append('ERROR! %s = %s' % (key,bitstatus))            
                
        if len(errmsg_list)>0:
            retval['msg'] = '\n'.join(errmsg_list)
        return retval

    def status_message(self):
        '''
        format the status info into a text
        '''
        status = self.status()
        if not status['status']:
            msg = 'PT Compressor is NOT okay!\n'
            msg += status['msg']
            return msg

        # status() already checked that everything is okay
        msg = ''
        for key in status.keys():
            if key!='status' and key!='msg':
                msg += '\n%s: %s' % (key,status[key])
                if key.find('alarm')>0 or key=='Solonoid' or key=='System ON':
                    msg += ' ... OK'
                    
        return msg

    def on(self):
        '''
        switch on the pulse tube compressor
        '''
        if not self.ok():
            print('ERROR!  Device not configured.')
            return False

        cmdkey = 'on'
        self.ser.write(self.command[cmdkey])
        ans = self.ser.readline()

        status = self.status()
        if status['status'] and 'System ON' in status.keys():
            if status['System ON']:
                print('Compressor is ON')
                return True
            else:
                print('Compressor is still OFF!')
                return False

        print('Could not verify status')
        return False

    def off(self):
        '''
        switch off the pulse tube compressor
        '''
        
        if not self.ok():
            print('ERROR!  Device not configured.')
            return False

        cmdkey = 'off'
        self.ser.write(self.command[cmdkey])
        ans = self.ser.readline()

        status = self.status()
        if status['status'] and 'System ON' in status.keys():
            if status['System ON']:
                print('Compressor is still ON!')
                return False
            else:
                print('Compressor is OFF')
                return True

        print('Could not verify status')
        return False
    

    def reset(self):
        '''
        reset the pulse tube compressor (clear alarms)
        '''
        if not self.ok():
            print('ERROR!  Device not configured.')
            return False

        cmdkey = 'reset'
        self.ser.write(self.command[cmdkey])
        ans = self.ser.readline()

        print(self.status_message())
        return
        
    

    
