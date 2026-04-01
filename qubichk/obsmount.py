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
import os,sys,socket,re,pickle
from datetime import timedelta
import datetime as dt
UTC = dt.timezone.utc
from time import sleep
from threading import Thread
import numpy as np
from satorchipy.datefunctions import utcnow, utcfromtimestamp
from qubichk.utilities import make_errmsg, get_known_hosts, hk_dir, get_myip, verify_directory
from qubicpack.pointing import position_key, position_offset, STX, interpret_pointing_chunk, axis_fullname
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
    axis_keys = list(position_offset.keys())
    n_axis_keys = len(axis_keys)
    datefmt = '%Y-%m-%dT%H:%M:%S UT'

    available_commands = ['ENA',    # enable
                          'DIS',    # disable
                          'START',  # start
                          'STOP',   # stop
                          'POS',    # go to position
                          'VEL']    # set velocity
    wait = 0.0 # seconds to wait before next socket command
    default_chunksize = 512 # motor PLC sends packets of approx 200 bytes each time
    sampleperiod = 100 # sample period in milliseconds (Note: PLC default is 1000 msec)
    verbosity = 1
    testmode = False

    elmin = 30 # minimum permitted elevation
    elmax = 70 # maximum permitted elevation
    azmin = -38 + position_offset['AZ'] # minimum permitted azimuth
    azmax = 398 + position_offset['AZ'] # maximum permitted azimuth (2026-02-12 15:49:34)
    azstep = 5 # default step size for azimuth movement for skydips

    pos_margin = 0.3 # default margin of precision for exiting the wait_for_arrival loop
    maxwait = 60 # default maximum wait time in seconds for wait_for_arrival loop, this is adjusted if it's a long slew

    
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
        
        self.acquire_pointing = False 
        self.client_address = None
        self.dumpfile_handle = None
        self.printmsg('obsmount python object initialized')
        return

    def printmsg(self,msg,threshold=0):
        '''
        print a message to screen
        '''
        if self.verbosity<threshold: return
        
        date_str = utcnow().strftime(self.datefmt)
        full_msg = '%s | obsmount: %s' % (date_str,msg)

        if self.logfile is not None:
            h = open(self.logfile,'a')
            h.write(full_msg+'\n')
            h.close()
        
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
            sleep(0.3)
            
        return retval

    def do_handshake(self,port='data',sampleperiod=None):
        '''
        do the handshake with the server
        '''
        self.printmsg('Doing handshake for port: %s' % port,threshold=2)
        retval = {}
        retval['ok'] = False
        if sampleperiod is None:
            sampleperiod = self.sampleperiod
        else:
            self.sampleperiod = sampleperiod

        # no handshake necessary for the PLC command port
        if port=='command':
            # for axis in self.axis_keys:
            #     retval = self.do_command_init(axis)
            #     if not retval['ok']: return retval
            self.error = None
            retval['ok'] = True
            self.printmsg('command port handshaking is not required')
            return retval

        self.printmsg('Doing handshake for port: data',threshold=2)

        # handshake for data stream
        sampleperiod_str = '%i' % sampleperiod
        try:
            nbytes = self.sock[port].send(sampleperiod_str.encode())
        except:
            retval['error'] = 'Failed to send sampling period to PLC on port %s' % port
            return self.return_with_error(retval)
        sleep(self.wait)
        # end handshake for data port
        
        retval['ok'] = True
        self.error = None
        self.printmsg('Handshake successful for PLC data port',threshold=2)
        return retval
                    
        

    def init_socket(self,port='data',sampleperiod=None):
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
            return self.return_with_error(retval)
        
        if port=='data':
            port_num = self.listen_port
            socktype = socket.SOCK_DGRAM
        else:
            port_num = self.command_port
            socktype = socket.SOCK_STREAM

        self.printmsg('creating socket for %s with type: %s' % (port,socktype),threshold=2)
        self.sock[port] = socket.socket(socket.AF_INET, socktype)
        self.sock[port].settimeout(0.5)
        self.printmsg('connecting to address: %s:%i' % (self.mount_ip,port_num),threshold=1)

        try:
            self.sock[port].connect((self.mount_ip,port_num))
        except socket.timeout:
            self.error = 'timeout'
        except:
            self.error = make_errmsg('SOCKET ERROR')
        else:
            self.printmsg('doing handshake after port connection',threshold=2)
            retval['ok'] = True
            retval = self.do_handshake(port,sampleperiod=sampleperiod)
            #if not retval['ok']: return self.return_with_error(retval)
            self.printmsg('setting subscribed to True for port: %s' % port,threshold=2)
            self.subscribed[port] = True
            self.error = None                      

        if self.error is None:
            retval['ok'] = True
            self.subscribed[port] = True
            return retval

        retval['error'] = 'could not communicate because of %s to %s:%s' % (self.error,self.mount_ip,port_num)
        return self.return_with_error(retval)

    
    def subscribe(self,port='data',sampleperiod=None):
        '''
        subscribe to the observation mount server
        the port is 'data' or 'command'
        '''

        retval = {}
        if not self.subscribed[port]:
            self.init_socket(port=port,sampleperiod=sampleperiod)
        
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

    def flush_data(self):
        '''
        flush the data stream from the PLC
        NOTE:  This is not used anymore since the implementation of acquisition() running in a thread
        to be deleted
        '''
        maxloop = 1000
        counter = 0
        now_tstamp = utcnow().timestamp()
        tstamp_delta = 1000.0
        tstamp_precision = 10*0.001*self.sampleperiod
        errmsg = 'NONE'
        
        while (tstamp_delta>tstamp_precision) and (errmsg.find('timeout')<0) and (counter<maxloop):
            azel = self.get_azel_from_plc()
            errmsg = azel['error']
            if not azel['ok']:
                break
            
            tstamp = azel['TIMESTAMP']
            tstamp_delta = now_tstamp-tstamp
        
        return azel
        

    def send_command(self,cmd_str):
        '''
        relay the command from the user to the rebroadcaster
        '''
        rebroadcaster_cmd = 'COMMAND_PLC:%s' % cmd_str
        ans = self.send_request_to_rebroadcaster(rebroadcaster_cmd)
        return ans
    
    def send_command_to_plc(self,cmd_str):
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
            self.printmsg('not subscribed to %s port.  subscribing now.' % port,threshold=1)
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
        self.printmsg('sending command: %s' % full_cmd_str,threshold=2)
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
        sleep(0.25)
        try:
            cmd_echo = self.sock[port].recv(1024)
        except:
            cmd_echo = make_errmsg('NO COMMAND ECHO')

        if isinstance(cmd_echo,bytes):
            cmd_echo = cmd_echo.decode().strip()

        retval['command echo'] = cmd_echo
        self.printmsg('response from PLC: %s' % cmd_echo,threshold=0)
        
        if cmd_echo.find('out of range')>=0:
            retval['error'] = cmd_echo
            return self.return_with_error(retval)

        if cmd_echo.find('already moving')>=0:
            retval['error'] = cmd_echo
            self.printmsg('ERROR! axis is already moving.  Please wait, or send "stop", and try again.')
            return self.return_with_error(retval)
        
        return retval

    def open_dumpfile(self,dump_dir=None):
        '''
        open the POINTING.dat file for fast acquisition and assign the dumpfile_handle
        '''
        dump_dir = verify_directory(dump_dir)
        if dump_dir is None:
            dump_dir = os.sep.join([os.environ['HOME'],'data'])
            dump_dir = verify_directory(dump_dir)        
        if dump_dir is None:
            dump_dir = hk_dir
            dump_dir = verify_directory(dump_dir)            
        if dump_dir is None:
            dump_dir = '/tmp'
            
        filename = os.sep.join([dump_dir,'POINTING.dat'])
        self.printmsg('pointing acquisition starting on file: %s' % filename,threshold=0)
        self.dumpfile_handle = open(filename,'ab')
        return dump_dir

    def close_dumpfile(self):
        '''
        close the POINTING.dat file, and reset the flags to stop dumping
        '''
        if self.dumpfile_handle is not None:
            self.dumpfile_handle.close()
            self.printmsg('pointing acquisition ended',threshold=0)
        else:
            self.printmsg('WARNING! no pointing acquisition to stop',threshold=1)
        self.dumpfile_handle = None
        return
    
    def acquisition(self):
        '''
        continuously acquire the data supplied by the mount PLC without any interpretation

        this is called by the PLC rebroadcaster and is run in a separate thread.  see listen_for_command()
        
        this is an infinite loop to be stopped by setting self.acquire_pointing=False
          which is done by sending a request to the PLC rebroadcaster:  see listen_for_command()

        it will send data to a client on request


        The loop acquires pointing data continuously and will dump to file if the file handle is defined
        NOTE: the data dumped here has not been corrected for encoder offset.
        See pointing in qubicpack:  https://github.com/satorchi/qubicpack/blob/master/qubicpack/pointing.py
        
        '''
        self.acquire_pointing = True
        while self.acquire_pointing:
            plc_data = self.get_data()
            if plc_data['ok']:
                packet = STX + plc_data['CHUNK']
                if self.dumpfile_handle is not None:
                    self.dumpfile_handle.write(packet)
                if self.client_address is not None:
                    azel = self.get_azel_from_plc(plc_data=plc_data)
                    azel_bytes = pickle.dumps(azel)
                    ack = self.reply_to_client(azel_bytes)
            else:
                if plc_data['error'].find('timeout')>=0:
                    self.printmsg('acquisition timeout',threshold=1)
                else:
                    self.printmsg('ERROR on PLC acquisition: %s' % plc_data['error'],threshold=0)
            
        return plc_data

    def reply_to_client(self,data_bytes,client_address=None):
        '''
        reply to a client request to the rebroadcaster
        this is called from listen_for_command()
        and also from acquisition()

        '''
        if client_address is None:
            client_address = self.client_address
        if client_address is None:
            return False
        
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        client_sock.settimeout(0.2)
        self.printmsg('REBROADCASTER sending info to %s:%i' % client_address,threshold=2)
        ack = True
        try:
            client_sock.sendto(data_bytes, client_address)
        except:
            self.printmsg('REBROADCASTER ERROR! Could not send info to %s:%i' % client_address,threshold=1)
            ack = False

        client_sock.close()
        self.client_address = None
        return ack
    
    def listen_for_command(self):
        '''
        listen for a command string arriving on socket and respond with data from the PLC
        This is the PLC rebroadcaster
        
        It is used to query the current mount position
        and also to start/stop the fast acquisition
        '''

        # first of all, start the fast acquisition loop
        acquisition_thread = Thread(target = self.acquisition)
        acquisition_thread.start()
        
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
            except socket.timeout:
                errmsg = 'socket timeout'
            except KeyboardInterrupt:
                errmsg = 'quitting the PLC re-broadcaster by Ctrl-C'
                keepgoing = False
                self.acquire_pointing = False
                sock.close()
                self.printmsg('REBROADCASTER: '+errmsg,threshold=0)
                break
            except:
                errmsg = make_errmsg('unknown error')
                
            if ans is None:
                self.printmsg('REBROADCASTER '+errmsg,threshold=1)
                continue
                

            ### verify the command
            cmdstr = None
            try:
                cmdstr, client_address = ans
            except:
                errmsg = make_errmsg('inappropriate response')

            if cmdstr is None:
                self.printmsg('REBROADCASTER '+errmsg,threshold=0)
                continue
            
            cmdstr_clean = ' '.join(cmdstr.decode().strip().split())
            received_date = utcnow()
            rx_date_str = received_date.strftime(self.datefmt)
            msg = 'REBROADCASTER received a request from %s at %s: %s' % (client_address[0],rx_date_str,cmdstr_clean)
            self.printmsg(msg,threshold=2)

            if cmdstr_clean=='EXIT SERVER':
                keepgoing = False
                self.close_dumpfile()
                self.acquire_pointing = False
                sock.close()
                self.printmsg('REBROADCASTER quitting',threshold=0)
                self.reply_to_client('quitting PLC re-broadcaster'.encode(),client_address)
                break

            if cmdstr_clean.find('DUMP=')==0:
                dumparglist = cmdstr_clean.split('=')
                if len(dumparglist)==2:
                    dump_dir = dumparglist[1]
                else:
                    dump_dir = None
                ##### set flag to start dumping (create the file handle)
                dump_dir = self.open_dumpfile(dump_dir)
                msg = 'started dumping to directory: %s' % dump_dir
                self.reply_to_client(msg.encode(),client_address)
                continue

            if cmdstr_clean.find('STOP DUMP')==0:
                self.close_dumpfile()
                self.reply_to_client('stopped dumping'.encode(),client_address)
                continue
            
            if cmdstr_clean=='GET AZEL':
                ### get position from the PLC and return it to the requester
                ### by assigning the client_address, the acquisition() loop will send the info back to the client
                self.client_address = client_address
                continue

            if cmdstr_clean.find('PLC_COMMAND:')==0:
                plc_cmd = cmdstr_clean.split('PLC_COMMAND:')[-1].strip()
                plc_ack = self.send_command_to_plc(plc_cmd)
                plc_ack_bytes = pickle.dumps(plc_ack)
                self.reply_to_client(plc_ack_bytes,client_address)
                continue

                
            self.printmsg('REBROADCASTER received inappropriate request',threshold=0)
            self.reply_to_client('inappropriate request'.encode(),client_address)

        return 
    
    
    
    def get_azel_from_plc(self,plc_data=None,chunksize=None):
        '''
        get the azimuth and elevation and return it with a timestamp

        this is probably an unnecessary wrapping, but I continue it for historical reasons
        this is called from the acquisition() loop

        plc_data is the return value from get_data()
        '''
        retval = {}
        retval['ok'] = True
        retval['error'] = 'NONE'


        if plc_data is None:
            plc_data = self.get_data(chunksize=chunksize)
            
        if not plc_data['ok']:
            return self.return_with_error(plc_data)

        packet = interpret_pointing_chunk(plc_data['CHUNK'])
        plc_data['DATA'] = packet
        
        errmsg = []
        errlevel = 0
        retval['TIMESTAMP'] = packet['TIMESTAMP']
        retval['data'] = plc_data

        for axis in self.axis_keys:
            if axis not in packet.keys() or len(packet[axis])==0:
                errmsg.append('no data for %s' % axis_fullname[axis])
                errlevel += 1
            else:
                retval[axis] = packet[axis][position_key[axis]] + position_offset[axis]
            
        retval['error'] = '\n'.join(errmsg)
        if errlevel >= 2:
            return self.return_with_error(retval)        
            
        return retval

    def get_azel(self):
        '''
        get azimuth and elevation by sending a query to the rebroadcast server
        '''
        ans = self.send_request_to_rebroadcaster('GET AZEL')
        return ans
        

    def send_request_to_rebroadcaster(self,cmd):
        '''
        send a request to the rebroadcaster
        see above: self.lisen_for_command ()
        '''
        retval = {}
        retval['ok'] = False
        retval['error'] = 'NONE'

        qc_ip = known_hosts['qubic-central']
        my_ip = get_myip()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.2)
        sock.sendto(cmd.encode(), (qc_ip, self.broadcast_request_port))
        
        ack = None
        try:
            ack, addr = sock.recvfrom(2048)
        except:
            errmsg = make_errmsg('no response from PLC rebroadcaster')
            retval['error'] = errmsg

        sock.close()
        if ack is None:
            return self.return_with_error(retval)

        # the returned acknowledgement might be a pickled dictionary
        ack_retval = None
        try:
            ack_retval = pickle.loads(ack)
        except:
            ack_retval = None

        if ack_retval is None:
            try:
                ack_retval = ack.decode()
            except:
                ack_retval = ack

        return ack_retval
        

    def show_azel(self):
        '''
        print the azimuth and elevation to screen
        '''
        ans = self.get_azel()
        if not ans['ok']:
            self.printmsg('AZ,EL = ERROR: %s' % ans['error'],threshold=0)
            return False

        self.printmsg('AZ,EL = %.3f %.3f' % (ans['AZ'],ans['EL']),threshold=0)
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
        cmd_az = az - position_offset['AZ']
        az_str = '%.1f' % cmd_az
        cmd_str = self.make_command_string('AZ','POS',az_str)
        return self.send_command(cmd_str)

    def goto_el(self,el):
        '''
        send command to move to the given elevation
        we correct for the encoder elevation offset
        '''
        cmd_el = el - position_offset['EL']
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
            cmd_str = self.make_command_string(axis,'STOP')
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
            cmd_str = self.make_command_string(axis,'ENA')
            self.send_command(cmd_str)
        return
        
    def disable(self):
        '''
        send command to disable all motors
        '''
        for axis in self.axis_keys:
            cmd_str = self.make_command_string(axis,'DIS')
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

        sleep(2)
        azel = self.get_azel()
        
        while not azel['ok']:
            sleep(2)
            now = utcnow().timestamp()
            azel = self.get_azel()
            if (now-tstart)>maxwait:
                errmsg = 'Could not get AZ,EL position after having retried for %.0f seconds' % maxwait
                azel['error'] = errmsg
                return self.return_with_error(azel)
        
        val = azel[key]

        # maximum wait time to get to target
        maxwait = 1.1*np.abs(val_final-val) + 5 # margin added to 1 deg/sec rotation speed
        if maxwait<self.maxwait: maxwait=self.maxwait # always have patience for at least the default maxwait (3 minutes)
        self.printmsg('using maximum wait time to reach target: %.1f secs' % maxwait,threshold=1)
        
        
        while np.abs(val-val_final)>self.pos_margin:
            sleep(2)
            now = utcnow().timestamp()
            if (now-tstart)>maxwait:
                errmsg = 'Exiting after maximum wait time: %.0f seconds' % maxwait
                errmsg += ' current value: %s = %.3f degrees' % (key,val)
                azel['error'] = errmsg
                return self.return_with_error(azel)
        
            azel = self.get_azel()
            if not azel['ok']:
                sleep(2)
                continue

            obsmount_tstamp = azel['TIMESTAMP']
            obsmount_date_str = utcfromtimestamp(obsmount_tstamp).strftime(self.datefmt)
            self.printmsg('[%s] AZ,EL = %.2f %.2f' % (obsmount_date_str,azel['AZ'],azel['EL']),threshold=0)

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
        # if axis still moving, wait a bit and try again
        if not ack['ok'] and ack['error'].find('already moving')>=0:
            sleep(5)
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
            sleep(2)
            azel = self.get_azel()
            now = utcnow().timestamp()
            if (now-start_tstamp)>10:
                azel['error'] = 'skydip unable to get current position: %s' % azel['error']
                return self.return_with_error(azel)
        
        
        az = azel['AZ']
        el = azel['EL']


        for azlimit in [azmax, azmin]:
        
            while (az<azmax) and (np.abs(az-azlimit)>self.pos_margin):
                ack = self.goto_el(elmax)

                # if axis still moving, wait a bit and try again
                if not ack['ok'] and ack['error'].find('already moving')>=0:
                    sleep(5)
                    ack = self.goto_el(elmax)
                
                sleep(1) # wait before next command
                azel = self.wait_for_arrival(el=elmax)
                if not azel['ok']:
                    azel['error'] = 'Did not successfully get to maximum elevation: %s' % azel['error']
                    return self.return_with_error(azel)

                ack = self.goto_el(elmin)
                sleep(1) # wait before next command
                azel = self.wait_for_arrival(el=elmin)
                if not azel['ok']:
                    azel['error'] = 'Did not successfully get to minimum elevation: %s' % azel['error']
                    return self.return_with_error(azel)

                az += azstep
                ack = self.goto_az(az)
                sleep(1)
                azel = self.wait_for_arrival(az=az)
                if not azel['ok']:
                    azel['error'] = 'Did not get to next azimuth position: %s' % azel['error']
                    return self.return_with_error(azel)
                    

            azstep = -azstep

        return azel
    

    def do_constant_elevation_scanning(self,el=None,azmin=None,azmax=None,tstart=None,tend=None,duration=None):
        '''
        do azimuth back and forth scanning at a given elevation

        ARGUMENTS:
         el       : elevation position during scanning
         azmin    : azimuth start position
         azmax    : azimuth end position
         tstart   : datetime object for start time (default is now)
         tend     : datetime object for end time (default is defined by duration)
         duration : duration in seconds.
             By default, this is a near endless loop and must be stopped manually with ctrl-c and do_end_observation.py
        '''
        if el is None: el = 50
        if azmin is None: azmin = 155
        if azmax is None: azmax = 205

        if tstart is None:
            start_time = utcnow()
        else:
            # correct for ambiguous timezone
            start_time = tstart.replace(tzinfo=UTC)

        if duration is None:
            duration_delta = timedelta(days=30) # must end observation manually
        else:
            duration_delta = timedelta(seconds=duration)

        if tend is None:
            end_time = start_time + duration_delta
        else:
            end_time = tend.replace(tzinfo=UTC)

        now = utcnow()
        while now<end_time:
            
            for azlimit in [azmax, azmin]:
                ack = self.goto_az(azlimit)

                # if axis still moving, wait a bit and try again
                if not ack['ok'] and ack['error'].find('already moving')>=0:
                    sleep(5)
                    ack = self.goto_az(azlimit)

                # still not ok, try to stop and restart
                if not ack['ok']:
                    ack = self.stop()
                    sleep(5)
                    ack = self.goto_az(azlimit)
                    
                sleep(1) # wait before next command
                azel = self.wait_for_arrival(az=azlimit)
                if not azel['ok']:
                    errmsg = 'Azimuth scan did not successfully get to azimuth position: %.3f degrees' % azlimit
                    self.printmsg(errmsg,threshold=0)
                    self.printmsg('Azimuth scan trying to send command one more time',threshold=0)
                    ack = self.goto_az(azlimit)
                    azel = self.wait_for_arrival(az=azlimit)
                    if not azel['ok']:
                        azel['error'] = errmsg+' after two attempts to send command'                    
                        return self.return_with_error(azel)

            now = utcnow()


        return True


    
