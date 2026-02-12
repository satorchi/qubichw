'''
$Id: obsmount.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 26 Nov 2025 11:02:41 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

class to read/command the Observation mount motors
now running the PLC instead of "motorcortex" on RaspberryPi

see documentation from Luciano Ferreyro and Lucia Sucunza
ANEXO-C_command_lists_PLC.pdf
ANEXO-C_monitor_data_PLC.pdf
QUBIC_Mount_General_documentation.pdf
email from Lucia: 2025-12-10/11, on elog: https://elog-qubic.in2p3.fr/demo/1294

'''
import os,sys,socket,time,re
import datetime as dt
import numpy as np
from satorchipy.datefunctions import utcnow
from qubichk.utilities import make_errmsg, get_known_hosts, hk_dir
from qubicpack.pointing import position_key, STX, interpret_pointing_chunk, axis_fullname
command_delimiter = ' '
known_hosts = get_known_hosts()
class obsmount:
    '''
    class to read to and command the observation mount
    '''
    
    mount_ip = known_hosts['motorplc']
    listen_port = 9180
    command_port = 9000
    qubicstudio_port = 4003 # port for receiving data from the red platform
    qubicstudio_ip = known_hosts['qubic-studio']
    # position offsets To Be Measured !!
    # 'EL': 49.315, # see elog: https://elog-qubic.in2p3.fr/demo/1296
    # 'EL': 49.935, # see elog: https://elog-qubic.in2p3.fr/demo/1321
    # 'AZ':  9.0    # see elog: https://elog-qubic.in2p3.fr/demo/1322 
    position_offset = {'AZ': 9.0, 
                       'EL': 49.935,
                       'RO': 0.0,
                       'TR': 0.0
                       }
    axis_keys = list(position_offset.keys())
    n_axis_keys = len(axis_keys)
    datefmt = '%Y-%m-%d-%H:%M:%S UT'

    available_commands = ['ENA',    # enable
                          'DIS',    # disable
                          'START',  # start
                          'STOP',   # stop
                          'POS',    # go to position
                          'VEL']    # set velocity
    wait = 0.0 # seconds to wait before next socket command
    default_chunksize = 512 # motor PLC sends packets of approx 200 bytes each time
    default_sampleperiod = 100 # sample period in milliseconds (Note: PLC default is 1000 msec)
    verbosity = 1
    testmode = False

    elmin = 30 # minimum permitted elevation
    elmax = 70 # maximum permitted elevation
    azmin = -38 # minimum permitted azimuth
    azmax = 398 # maximum permitted azimuth (2026-02-12 15:49:34)
    azstep = 5 # default step size for azimuth movement for skydips

    pos_margin = 0.1 # default margin of precision for exiting the wait_for_arrival loop
    maxwait = 180 # default maximum wait time in seconds for wait_for_arrival loop

    
    def __init__(self):
        '''
        instantiate the class with some default values
        '''
        self.sock = {}
        self.sock['data'] = None
        self.sock['command'] = None
        self.subscribed = {}
        self.subscribed['data'] = False
        self.subscribed['command'] = False
        
        return

    def printmsg(self,msg):
        '''
        print a message to screen
        '''
        if self.verbosity<1: return
        
        date_str = utcnow().strftime(self.datefmt)
        print('%s | obsmount: %s' % (date_str,msg))
        return

    def return_with_error(self,retval):
        '''
        print a message and return the error code and stuff in a dictionary
        '''
        retval['ok'] = False
        if retval['error'].find('KeyboardInterrupt')>=0:
            self.printmsg('Ending by Ctrl-C')
        else:
            self.printmsg('ERROR! %s' % retval['error'])
        return retval

    def do_command_init(self,axname):
        '''
        do the command initialization commands
        '''
        for cmd_arg in ['ENA','START','VEL 1']:
            cmd = '%s %s' % (axname,cmd_arg)
            retval = self.send_command(cmd)
            if not retval['ok']: return retval
            
        return retval

    def do_handshake(self,port='data',sampleperiod=None):
        '''
        do the handshake with the server
        '''
        retval = {}
        retval['ok'] = False
        if sampleperiod is None: sampleperiod = self.default_sampleperiod

        # no handshake necessary for the PLC command port
        if port=='command':
            for axis in self.axis_keys:
                retval = self.do_command_init(axis)
                if not retval['ok']: return retval
            self.error = None
            self.printmsg('command port initialized')
            return retval
        
        sampleperiod_str = '%i' % sampleperiod
        try:
            nbytes = self.sock[port].send(sampleperiod_str.encode())
        except:
            retval['error'] = 'Failed to send sampling period to PLC on port %s' % port
            return self.return_with_error(retval)
        time.sleep(self.wait)
        # end handshake for data port
        
        retval['ok'] = True
        self.error = None
        self.printmsg('Handshake successful for PLC data port')
        return retval
                    
        

    def init_socket(self,port='data'):
        '''
        initialize the communication socket
        the port is either 'data' or 'command'
        '''
        retval = {}
        retval['ok'] = False
        retval['error'] = 'init error'
        self.error = None
        
        if port=='data':
            port_num = self.listen_port
            socktype = socket.SOCK_DGRAM
        else:
            port_num = self.command_port
            socktype = socket.SOCK_STREAM

        self.printmsg('creating socket with type: %s' % socktype)
        self.sock[port] = socket.socket(socket.AF_INET, socktype)
        self.sock[port].settimeout(0.1)
        self.printmsg('connecting to address: %s:%i' % (self.mount_ip,port_num))
        try:
            self.sock[port].connect((self.mount_ip,port_num))
        except socket.timeout:
            self.subscribed[port] = False
            self.error = 'TIMEOUT'
        except:
            self.subscribed[port] = False
            self.error = make_errmsg('SOCKET ERROR')
        else:
            retval = self.do_handshake(port)
            if not retval['ok']: return self.return_with_error(retval)
            self.subscribed[port] = True
            self.error = None                      

        if self.error is None:
            retval['ok'] = True
            return True

        retval['error'] = 'could not communicate because of %s to %s:%s' % (self.error,self.mount_ip,port_num)
        return self.return_with_error(retval)

    
    def subscribe(self,port='data'):
        '''
        subscribe to the observation mount server
        the port is 'data' or 'command'
        '''

        retval = {}
        if not self.subscribed[port]:
            self.init_socket(port=port)
        
        # check that the socket is valid
        if not self.subscribed[port]:
            retval['error'] = 'could not subscribe for %s' % port
            return self.return_with_error(retval)

        return self.subscribed[port]

    def disconnect(self):
        '''
        disconnect the ports
        '''
        for port in ['data','command']:
            if not self.subscribed[port]: continue
            self.sock[port].close()
            self.sock[port] = None
            self.subscribed[port] = False
        return None

    def get_data(self,chunksize=None):
        '''
        once we're subscribed, we can listen for the data
        
        The chunksize is the number of bytes to read.
        '''
        if chunksize is None: chunksize = self.default_chunksize
        port = 'data'
        retval = {}
        retval['ok'] = True
        retval['error'] = 'NONE'
        retval['CHUNK TIMESTAMP'] = utcnow().timestamp()
        retval['DATA'] = None
        retval['CHUNK'] = bytearray([]) # initialize with empty chunk

        # check that we are subscribed
        if not self.subscribed[port]:
            self.subscribe(port='data')

        if not self.subscribed[port]:
            retval['error'] = 'could not subscribe'
            return self.return_with_error(retval)

        try:
            dat = self.sock[port].recv(chunksize)
        except socket.timeout:
            self.subscribed[port] = False
            retval['error'] = 'get_data: socket timeout'
            return self.return_with_error(retval)
        except KeyboardInterrupt:
            self.subscribed[port] = False
            retval['error'] = 'Detected keyboard interrupt Ctrl-C'
            return self.return_with_error(retval)
        except:
            self.subscribed[port] = False
            retval['error'] = make_errmsg('could not get az,el data')
            return self.return_with_error(retval)


        retval['CHUNK'] = dat
        return retval
    
    def send_command(self,cmd_str):
        '''
        send a command to the observation mount
        '''
        port = 'command'
        retval = {}
        retval['ok'] = True
        retval['error'] = 'NONE'
        retval['command'] = cmd_str

        # check that we are subscribed
        if not self.subscribed[port]:
            self.subscribe(port)

        if not self.subscribed[port]:
            retval['error'] = 'could not subscribe'
            return self.return_with_error(retval)

        cmd_list = cmd_str.split(command_delimiter)
        if len(cmd_list)<2:
            retval['error'] = 'not enough arguments for command: %s' % cmd_str
            return self.return_with_error(retval)

        axis = cmd_list[0]
        cmd = cmd_list[1]
        if cmd not in self.available_commands:
            retval['error'] = 'Invalid command: %s' % cmd
            return self.return_with_error(retval)

        full_cmd_str = '%s' % cmd_str.upper()
        self.printmsg('sending command: %s' % full_cmd_str)
        if self.testmode:
            self.printmsg("TESTMODE:  I didn't really send the command")
            return retval
        
        try:
            self.sock[port].sendall(full_cmd_str.encode())
        except:
            self.subscribed[port] = False
            retval['error'] = make_errmsg('command unsuccessful')
            return self.return_with_error(retval)

        return retval

    def acquisition(self,dump_dir=hk_dir):
        '''
        dump the data supplied by the mount PLC without any interpretation
        this is an infinite loop to be interrupted by ctrl-c, or socket error, but not timeout error
        
        this replaces dump_data above and has lower overhead
        '''
        filename = os.sep.join([dump_dir,'POINTING.dat'])
        self.printmsg('pointing acquisition starting on file: %s' % filename)
        h = open(filename,'ab')
        ans = self.get_data()
        keepgoing = True
        while keepgoing:
            packet = STX + ans['CHUNK']
            h.write(packet)
            ans = self.get_data()
            keepgoing = ans['ok']
            if (not ans['ok']) and (ans['error'].find('timeout')>=0):
                self.printmsg('acquisition timeout')
                keepgoing = True

        h.close()
        self.printmsg('pointing acquisition ended: %s' % ans['error'])
        return ans
    
    def get_azel(self,chunksize=None):
        '''
        get the azimuth and elevation and return it with a timestamp
        '''
        retval = {}
        retval['ok'] = True
        retval['error'] = 'NONE'

        ans = self.get_data(chunksize=chunksize)
        if not ans['ok']:
            return self.return_with_error(ans)

        packet = interpret_pointing_chunk(ans['CHUNK'])
        ans['DATA'] = packet
        
        errmsg = []
        errlevel = 0
        retval['TIMESTAMP'] = packet['TIMESTAMP']
        retval['data'] = ans

        for axis in self.axis_keys:
            if axis not in packet.keys() or len(packet[axis])==0:
                errmsg.append('no data for %s' % axis_fullname[axis])
                errlevel += 1
            else:
                retval[axis] = packet[axis][position_key[axis]] + self.position_offset[axis]
            
        retval['error'] = '\n'.join(errmsg)
        if errlevel >= 2:
            return self.return_with_error(retval)        
            
        return retval

    def show_azel(self):
        '''
        print the azimuth and elevation to screen
        '''
        ans = self.get_azel()
        if not ans['ok']:
            self.printmsg('AZ,EL = ERROR: %s' % ans['error'])
            return False

        self.printmsg('AZ,EL = %.3f %.3f' % (ans['AZ'],ans['EL']))
        return True


    def get_position(self):
        '''
        for compatibility with platform.py for the red mount
        '''
        azel = self.get_azel()
        if not azel['ok']:
            az = 'bad answer'
            el = 'bad answer'
            azwarn = True
            elwarn = True
            return az,el,azwarn,elwarn

        az = azel['AZ']
        el = azel['EL']
        azwarn = False
        elwarn = False
        return az,el,azwarn,elwarn


    def is_connected(self,port='data'):
        '''
        return status of connection
        '''
        return self.subscribed[port]

    def make_command_string(self,axis,cmd,val=None):
        '''
        make the command string
        note that val is converted to string
        '''
        if val is None:
            cmd_str = command_delimiter.join([axis.upper(),cmd.upper()])
        else:
            cmd_str = command_delimiter.join([axis.upper(),cmd.upper(),str(val)])
        return cmd_str
    
    def goto_az(self,az):
        '''
        send command to move to the given azimuth
        we correct for the encoder azimuth offset
        '''
        cmd_az = az - self.position_offset['AZ']
        az_str = '%.1f' % cmd_az
        cmd_str = self.make_command_string('AZ','POS',az_str)
        return self.send_command(cmd_str)

    def goto_el(self,el):
        '''
        send command to move to the given elevation
        we correct for the encoder elevation offset
        '''
        cmd_el = el - self.position_offset['EL']
        el_str = '%.1f' % cmd_el
        cmd_str = self.make_command_string('EL','POS',el_str)
        return self.send_command(cmd_str)

    def set_az_speed(self,speed):
        '''
        send command to set the azimuth speed
        '''
        speed_str = '%.1f' % speed
        cmd_str = self.make_command_string('AZ','VEL',speed_str)
        return self.send_command(cmd_str)
    
    def set_el_speed(self,speed):
        '''
        send command to set the elevation speed
        '''
        speed_str = '%.1f' % speed
        cmd_str = self.make_command_string('EL','VEL',speed_str)
        return self.send_command(cmd_str)
    
    def stop(self):
        '''
        send command to stop all movement
        '''
        for axis in self.axis_keys:
            cmd_str = self.make_command_str(axis,'STOP')
            self.send_command(cmd_str)
        return

    def abort(self):
        '''
        send command to abort current command
        '''
        return self.stop()

    def do_homing(self):
        '''
        send command to do the homing (go to the limit switch)
        '''
        return self.send_command('DOHOMING')

    def enable(self):
        '''
        send command to enable all motors
        '''
        for axis in self.axis_keys:
            cmd_str = self.make_command_str(axis,'ENA')
            self.send_command(cmd_str)
        return
        
    def disable(self):
        '''
        send command to disable all motors
        '''
        for axis in self.axis_keys:
            cmd_str = self.make_command_str(axis,'DIS')
            self.send_command(cmd_str)
        return

    def wait_for_arrival(self,az=None,el=None,maxwait=None):
        '''
        wait for telescope to get into requested position
        '''
        tstart = utcnow().timestamp()
        if maxwait is None: maxwait = self.maxwait

        az_final = az
        el_final = el

        if (az_final is None) and (el_final is None):
            print('Please specify one of az or el with option az=<value> or el=<value>')
            return

        if az_final is not None:
            key = 'AZ'
            val_final = az_final
        else:
            key = 'EL'
            val_final = el_final

        time.sleep(2)
        azel = self.get_azel()
        
        while not azel['ok']:
            time.sleep(2)
            now = utcnow().timestamp()
            azel = self.get_azel()
            if (now-tstart)>maxwait:
                self.printmsg('Error! Could not get AZ,EL position.')
                return False
        
        val = azel[key]

        while np.abs(val-val_final)>self.pos_margin:
            time.sleep(2)
            now = utcnow().timestamp()
            if (now-tstart)>maxwait:
                self.printmsg('Maximum wait time')
                return False
        
            azel = self.get_azel()
            if not azel['ok']:
                time.sleep(2)
                continue

            self.printmsg('AZ,EL = %.2f %.2f' % (azel['AZ'],azel['EL']))

            val = azel[key]

        return True
        
    
    def do_skydip_sequence(self,azstep=None):
        '''
        do the sky dip movements
        '''
        if azstep is None: azstep = self.azstep
    
        start_tstamp = utcnow().timestamp()

        ack = self.goto_az(self.azmin)
        if not ack['ok']:
            return False
        
        azok = self.wait_for_arrival(az=self.azmin)
        if not azok:
            self.printmsg('ERROR! Did not successfully get to starting azimuth position')
            return False

        self.goto_el(self.elmin)
        elok = self.wait_for_arrival(el=self.elmin)
        if not elok:
            self.printmsg('ERROR! Did not successfully get to starting elevation position')
            return False

        azel = self.get_azel()
        while not azel['ok']:
            time.sleep(2)
            azel = self.get_azel()
            now = utcnow().timestamp()
            if (now-start_tstamp)>10:
                self.printmsg('ERROR! Could not get current position.')
                return False
        
        
        az = azel['AZ']
        el = azel['EL']


        for azlimit in [self.azmax, self.azmin]:
        
            while np.abs(az-azlimit)>self.pos_margin:
                self.goto_el(self.elmax)
                time.sleep(1) # wait before next command
                elok = self.wait_for_arrival(el=self.elmax)
                if not elok:
                    self.printmsg('ERROR! Did not successfully get to starting elevation position')
                    return False
            

                self.goto_el(self.elmin)
                azok = self.wait_for_arrival(el=self.elmin)
                if not azok:
                    self.printmsg('ERROR! Did not successfully get to starting azimuth position')
                    return False

                az += azstep
                self.goto_az(az)
                self.wait_for_arrival(az=az)

            azstep = -azstep

        return True
    
