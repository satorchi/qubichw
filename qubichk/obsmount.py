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
import os,sys,socket,time,re,pickle
from datetime import timedelta
import numpy as np
from satorchipy.datefunctions import utcnow
from qubichk.utilities import make_errmsg, get_known_hosts, hk_dir, get_myip, verify_directory
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
    broadcast_request_port = 61337
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

    pos_margin = 0.3 # default margin of precision for exiting the wait_for_arrival loop
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
        log_dir = os.sep.join([os.environ['HOME'],'log'])
        log_dir = verify_directory(log_dir)
        if log_dir is None:
            log_dir = verify_directory('/tmp')
        if log_dir is None:
            self.logfile = None
        else:
            self.logfile = os.sep.join([log_dir,'obsmount_log.txt'])
        
        
        return

    def printmsg(self,msg):
        '''
        print a message to screen
        '''
        date_str = utcnow().strftime(self.datefmt)
        full_msg = '%s | obsmount: %s' % (date_str,msg)

        if self.logfile is not None:
            h = open(self.logfile,'a')
            h.write(full_msg+'\n')
            h.close()
        if self.verbosity<1: return
        
        print(full_msg)
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
            time.sleep(0.3)
            
        return retval

    def do_handshake(self,port='data',sampleperiod=None):
        '''
        do the handshake with the server
        '''
        self.printmsg('Doing handshake for port: %s' % port)
        retval = {}
        retval['ok'] = False
        if sampleperiod is None: sampleperiod = self.default_sampleperiod

        # no handshake necessary for the PLC command port
        if port=='command':
            # for axis in self.axis_keys:
            #     retval = self.do_command_init(axis)
            #     if not retval['ok']: return retval
            self.error = None
            retval['ok'] = True
            self.printmsg('command port handshaking is not required')
            return retval

        self.printmsg('Doing handshake for port: data')

        # handshake for data stream
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

        if self.subscribed[port]:
            retval['error'] = 'already subscribed to port: %s' % port
            self.return_with_error(retval)
        
        if port=='data':
            port_num = self.listen_port
            socktype = socket.SOCK_DGRAM
        else:
            port_num = self.command_port
            socktype = socket.SOCK_STREAM

        self.printmsg('creating socket for %s with type: %s' % (port,socktype))
        self.sock[port] = socket.socket(socket.AF_INET, socktype)
        self.sock[port].settimeout(0.5)
        self.printmsg('connecting to address: %s:%i' % (self.mount_ip,port_num))

        # we set the "subscribed" flag to True, just for trying because the PLC doesn't like multiple attempts
        self.subscribed[port] = True
        self.printmsg('setting subscribed to True just for trying on port: %s' % port)
        try:
            self.sock[port].connect((self.mount_ip,port_num))
        except socket.timeout:
            self.error = 'TIMEOUT'
        except:
            self.error = make_errmsg('SOCKET ERROR')
        else:
            self.printmsg('doing handshake after port connection')
            retval['ok'] = True
            retval = self.do_handshake(port)
            #if not retval['ok']: return self.return_with_error(retval)
            self.printmsg('setting subscribed to True for port: %s' % port)
            self.subscribed[port] = True
            self.error = None                      

        if self.error is None:
            retval['ok'] = True
            self.subscribed[port] = True
            return retval

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

    def unsubscribe(self):
        '''
        alias for disconnect
        '''
        return self.disconnect()

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
            retval['error'] = 'could not subscribe to data stream'
            return self.return_with_error(retval)

        try:
            dat = self.sock[port].recv(chunksize)
        except socket.timeout:
            retval['error'] = 'get_data: socket timeout'
            return self.return_with_error(retval)
        except KeyboardInterrupt:
            retval['error'] = 'Detected keyboard interrupt Ctrl-C'
            return self.return_with_error(retval)
        except:
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
            self.printmsg('not subscribed to %s port.  subscribing now.' % port)
            self.subscribe(port)

        if not self.subscribed[port]:
            retval['error'] = 'could not subscribe to command port'
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

        # try to get the command echo
        time.sleep(0.25)
        try:
            cmd_echo = self.sock[port].recv(1024)
        except:
            cmd_echo = 'NO COMMAND ECHO'

        if isinstance(cmd_echo,bytes):
            cmd_echo = cmd_echo.decode()

        retval['command echo'] = cmd_echo
        if cmd_echo.find('out of range')>=0:
            retval['error'] = cmd_echo
            self.return_with_error(retval)
        return retval

    def acquisition(self,dump_dir=hk_dir):
        '''
        dump the data supplied by the mount PLC without any interpretation
        this is an infinite loop to be interrupted by ctrl-c, or socket error, but not timeout error
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

    def broadcast_data(self):
        '''
        get data from the PLC and rebroadcast it to a local port
        '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        PORT = self.broadcast_port
        rx = get_myip()
        while True:
            chunkdat = self.get_data()
            if not chunkdat['ok']:
                if chunkdat['error'].find('Ctrl-C')>0:
                    sock.close()
                    return
                time.sleep(0.25)
                continue
                
            time.sleep(0.05)
            sock.sendto(chunkdat['CHUNK'],(rx,PORT))

        # never reach this point
        sock.close()
        return

    def listen_for_command(self):
        '''
        listen for a command string arriving on socket and respond with data from the PLC
        This is the slow re-broadcast
        '''

        my_ip = get_myip()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(None)
        sock.bind((my_ip, self.broadcast_request_port))

        now = utcnow()
        keepgoing = True
        while keepgoing:
            ans = None

            ### listen for a command
            try:
                ans = sock.recvfrom(1024)
            except socket.error:
                errmsg = make_errmsg('socket error')
            except:
                errmsg = make_errmsg('unknown error')
                
            if ans is None:
                self.printmsg(errmsg)
                continue
                

            ### verify the command
            cmdstr = None
            try:
                cmdstr, addr_tple = ans
            except:
                errmsg = make_errmsg('inappropriate response')

            if cmdstr is None:
                self.printmsg(errmsg)
                continue
            
            addr = addr_tple[0]
            client_port = addr_tple[1]
            cmdstr_clean = ' '.join(cmdstr.decode().strip().split())
            self.printmsg('received a request from %s at %s: %s' % (addr,received_date.strftime(self.datefmt),cmdstr_clean))

            if cmdstr_clean=='EXIT SERVER':
                keepgoing = False
                sock.close()
                break
            
            if cmdstr_clean!='GET AZEL':
                self.printmsg('inappropriate request')
                continue

            ### get position from the PLC and return it to the requester
            azel = self.get_azel_from_plc()
            azel_bytes = pickle.dumps(azel)

            client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            client_sock.settimeout(0.2)
            self.printmsg('sending position info')
            try:
                client_sock.sendto(azel_bytes, (addr, client_port))
            except:
                self.printmsg('Error! Could not send acknowledgement to %s:%i' % (addr,client_port))

            client_sock.close()
        return 
    
    
    
    def get_azel_from_plc(self,chunksize=None):
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

    def get_azel(self):
        '''
        get azimuth and elevation by sending a query to the rebroadcast server
        '''
        retval = {}
        retval['ok'] = False
        retval['error'] = 'NONE'
        

        cmd = 'GET AZEL'

        qc_ip = known_hosts['qubic-central']
        my_ip = get_myip()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.2)
        sock.sendto(cmd.encode(), (qc_ip, self.broadcast_request_port))

        
        sock.bind((my_ip, self.broadcast_request_port))
        ack = None
        try:
            ack, addr = sock.recvfrom(1024)
        except:
            retval['error'] = 'no response from PLC rebroadcaster'
            self.return_with_error(retval)

        azel = pickle.loads(ack)
        sock.close()
        return azel
        

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

        ##### temporary until I implement the PLC rebroadcaster
        retval = {}
        retval['ok'] = True
        retval['error'] = 'just waiting the maximum until I implement the PLC rebroadcaster'
        time.sleep(maxwait)
        return retval
        

        az_final = az
        el_final = el

        if (az_final is None) and (el_final is None):
            print('Please specify one of az or el with option az=<value> or el=<value>')
            retval = {}
            retval['ok'] = False
            retval['error'] = 'insufficient input to wait_for_arrival'
            return self.return_with_error(retval)

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
                errmsg = 'Could not get AZ,EL position after having retried for %.0f seconds' % maxwait
                azel['error'] = errmsg
                return self.return_with_error(azel)
        
        val = azel[key]

        while np.abs(val-val_final)>self.pos_margin:
            time.sleep(2)
            now = utcnow().timestamp()
            if (now-tstart)>maxwait:
                errmsg = 'Exiting after maximum wait time: %.0f seconds' % maxwait
                errmsg += '      current value: %s = %.3f degrees' % (key,val)
                azel['error'] = errmsg
                return self.return_with_error(azel)
        
            azel = self.get_azel()
            if not azel['ok']:
                time.sleep(2)
                continue

            self.printmsg('AZ,EL = %.2f %.2f' % (azel['AZ'],azel['EL']))

            val = azel[key]

        return azel
        
    
    def do_skydip_sequence(self,azstep=None,azmin=None,azmax=None,elmin=None,elmax=None):
        '''
        do the sky dip movements
        '''
        if azstep is None: azstep = self.azstep
        if azmin is None:  azmin  = self.azmin
        if azmax is None:  azmax  = self.azmax
        if elmin is None:  elmin  = self.elmin
        if elmax is None:  elmax  = self.elmax
        
    
        start_tstamp = utcnow().timestamp()

        ack = self.goto_az(azmin)
        if not ack['ok']:
            return ack
        
        azel = self.wait_for_arrival(az=azmin)
        if not azel['ok']:
            azel['error'] = 'Did not successfully get to starting azimuth position: %s' % azel['error']
            return self.return_with_error(azel)

        self.goto_el(elmin)
        azel = self.wait_for_arrival(el=elmin)
        if not azel['ok']:
            azel['error'] = 'Did not successfully get to starting elevation position: %s' % azel['error']
            return self.return_with_error(azel)

        azel = self.get_azel()
        while not azel['ok']:
            time.sleep(2)
            azel = self.get_azel()
            now = utcnow().timestamp()
            if (now-start_tstamp)>10:
                azel['error'] = 'skydip unable to get current position: %s' % azel['error']
                return self.return_with_error(azel)
        
        
        az = azel['AZ']
        el = azel['EL']


        for azlimit in [azmax, azmin]:
        
            while np.abs(az-azlimit)>self.pos_margin:
                self.goto_el(elmax)
                time.sleep(1) # wait before next command
                azel = self.wait_for_arrival(el=elmax)
                if not azel['ok']:
                    azel['error'] = 'Did not successfully get to starting elevation position: %s' % azel['error']
                    return self.return_with_error(azel)
            

                self.goto_el(elmin)
                azel = self.wait_for_arrival(el=elmin)
                if not azel['ok']:
                    azel['error'] = 'Did not successfully get to starting azimuth position: %s' % azel['error']
                    return self.return_with_error(azel)

                az += azstep
                self.goto_az(az)
                azel = self.wait_for_arrival(az=az)
                if not azel['ok']:
                    azel['error'] = 'Did not get to next azimuth position: %s' % azel['error']
                    return self.return_with_error(azel)
                    

            azstep = -azstep

        return azel
    

    def do_constant_elevation_scanning(self,el=None,azmin=None,azmax=None,duration=None):
        '''
        do azimuth back and forth scanning at a given elevation

        ARGUMENTS:
         el       : elevation position during scanning
         azmin    : azimuth start position
         azmax    : azimuth end position
         duration : duration in seconds.
             By default, this is a near endless loop and must be stopped manually with ctrl-c and do_end_observation.py
        '''
        if el is None: el = 50
        if azmin is None: azmin = 155
        if azmax is None: azmax = 205
        if duration is None:
            duration_delta = timedelta(days=30) # must end observation manually
        else:
            duration_delta = timedelta(seconds=duration)
    
        start_tstamp = utcnow().timestamp()

        ack = self.goto_el(el)
        if not ack['ok']: return self.return_with_error(ack)
        azel = self.wait_for_arrival(el=el)
        if not azel['ok']:
            azel['error'] = 'Did not successfully get to elevation position: %.3f degrees' % el
            return self.return_with_error(azel)


        # maximum wait time for each scan
        maxwait = np.abs(azmax-azmin)/0.9 + 5 # margin added to 1 deg/sec rotation speed
        self.printmsg('using wait time for each azimuth scan: %.1f secs' % maxwait)
        
        ack = self.goto_az(azmin)
        if not ack['ok']:
            ack['error'] = 'Scan unable to send command'
            return self.return_with_error(ack)
        
        azel = self.wait_for_arrival(az=azmin,maxwait=maxwait)
        if not azel['ok']:
            azel['error'] = 'Scan did not successfully get to starting azimuth position: %.3f degrees' % azmin
            return self.return_with_error(azel)

        now = utcnow()
        end_time = now + duration_delta
        while now<end_time:
            
            for azlimit in [azmax, azmin]:
                ack = self.goto_az(azlimit)
                time.sleep(1) # wait before next command
                azel = self.wait_for_arrival(az=azlimit,maxwait=maxwait)
                if not azel['ok']:
                    azel['error'] = 'Scan did not successfully get to azimuth position: %.3f degrees' % azlimit
                    return self.return_with_error(azel)

            now = utcnow()


        return True


    
