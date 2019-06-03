#!/usr/bin/env python
'''
$Id: horn_monitor.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 25 Apr 2019 14:16:09 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

receive the inductance data from the horn switches, and plot
'''
from __future__ import division, print_function
import os,sys,time,struct,socket
import datetime as dt
from glob import glob
import numpy as np
from matplotlib import pyplot as plt
from astropy.io import fits
import gnuplotlib as gp

from satorchipy.datefunctions import str2dt

class horn_monitor:
    '''
    class for socket reception of horn switch info
    '''

    date_fmt = '%Y-%m-%d %H:%M:%S.%f'
    if 'HOME' in os.environ:
        homedir = os.environ['HOME']
    else:
        homedir = '/tmp'
    
    interrupt_flag_file = '%s/__STOP_MONITORING_HORNS__' % homedir

    def __init__(self,plot_type='x',timeout=None):
        '''
        initialize the horn_monitor object
        '''
        
        if os.path.isfile(self.interrupt_flag_file):
            os.remove(self.interrupt_flag_file)
        self.plot_type = plot_type
        self.client = None
        self.s = None
        self.timeout = timeout
        self.fig = None
        self.ax = None
        self.init_data()
        return None

    def init_data(self):
        '''
        initialize the data and header
        '''
        self.dat = -np.ones(4096)
        self.header = {}
        self.header['HORN_ID'] = None
        self.header['IS_GOOD'] = None
        self.header['CHANNEL'] = None
        return


    def listen_to_horns(self):
        '''
        listen for the inductance data arriving on socket
        '''
        previous = dt.datetime.utcfromtimestamp(0)
        double_horn_change_time = dt.timedelta(seconds=1)
    
        # setup the plot
        self.setup_horn_plot()
    
        # setup the socket
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.settimeout(self.timeout)
        self.s.bind(('',37000))
        self.s.listen(1)

        print('waiting for horn stuff')
        try:
            self.client, addr = self.s.accept()
            print('got client')
        except KeyboardInterrupt:
            print('interrupted with ctrl-c')
            return

        subcounter = 0
        counter = 0
        print('going into loop. Ctrl-C to interrupt.')

        while not os.path.isfile(self.interrupt_flag_file):
            #### get data ###############################
            if self.timeout is None:
                print('waiting for acknowledgement')
            else:
                print('waiting up to %.0f seconds for acknowledgement' % self.timeout)
        
            try:
                retval = self.next_action()
            except KeyboardInterrupt:
                print('interrupted with ctrl-c')
                break

            if retval=='KeyboardInterrupt': break
            
            now = dt.datetime.utcnow()
            tstamp = float(now.strftime('%s.%f'))
            self.write_horn_fits(tstamp)
            #############################################

            #### plot ###################################
            delta = now - previous
            if delta > double_horn_change_time: self.reset_horn_plot()    
            self.plot_horn_action()
            #############################################

            counter += 1
            previous = now
        #### end of loop ###################

        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()

        print('recorded %i events' % counter)
        return

    def next_action(self):
        '''
        get the next event

        for data unpacking, see email from Andrea Passerini, 2019-06-02:

        Now the preamble packet is made from 8 bytes.
        The former 4 represent the waveform lenght as you've already used.
        Then:
            2 bytes for the horn ID
            1 byte for good (0x01) or bad(0x00)
            1 byte for the belonging measurement channel 0x00 or 0x01.
        
        '''
        self.init_data()

        print('waiting for horn action...')
        try:
            id_packet = self.client.recv(8)
        except KeyboardInterrupt:
            print('interrupted with ctrl-c')
            return 'KeyboardInterrupt'
        except socket.error:
            print('ignoring socket error')
            return 'SocketError'
        except:
            print('ignoring some kind of error')
            return 'UnknownError'

        
        print('length of id_packet: %i' % len(id_packet))
        print('id_packet type: %s' % type(id_packet))
        print('id_packet: %s' % str(id_packet))
                
        nbytes_bin = id_packet[0:4]
        horn_id_bin = id_packet[4:6]
        good_bin = id_packet[6:7]
        chan_bin = id_packet[7:8]

        if len(horn_id_bin)==2:
            self.header['HORN_ID'] = struct.unpack('>H',horn_id_bin)[0]
        if len(good_bin)==1:
            self.header['IS_GOOD'] = struct.unpack('>B',good_bin)[0]
        if len(chan_bin)==1:
            self.header['CHANNEL'] = struct.unpack('>B',chan_bin)[0]
        
        if len(nbytes_bin)==4:
            nbytes = struct.unpack('>L',nbytes_bin)[0]
            
            print('trying to get %i bytes' % nbytes)
            dat_bin = ''
            for idx in range(nbytes):
                byte = self.client.recv(1)
                dat_bin += byte
            nbytes = len(dat_bin)
            print('data received is %i bytes' % nbytes)
            npts = nbytes//4
            fmt = '>%iL' % npts
            print('unpacking data array of %i elements' % npts)
            self.dat = np.array(struct.unpack(fmt,dat_bin))            
            return 'NormalReturn'
        return 'UnpackError'


    def setup_horn_plot(self):
        '''
        setup a matplotlib plot on screen
        '''
        if self.plot_type=='ascii': return
        
        print('setting up plot window')
        plt.ion()
        self.fig = plt.figure(figsize=(9,6))
        self.fig.canvas.set_window_title('plt: horn switch inductor profile')
        self.fig.add_axes((0.1,0.1,0.85,0.8))
        self.ax = self.fig.axes[0]
        self.fig.suptitle('Horn switch inductor profile')
        self.ax.set_xlabel('time / $\mu$secs')
        self.ax.set_ylabel('level / arbitrary units')
        plt.pause(0.01)
        
        return

    def reset_horn_plot(self):
        '''
        clear the plot before making a new one
        '''
        if self.plot_type=='ascii': return
        
        self.ax.cla()
        self.ax.set_xlabel('time')
        self.ax.set_ylabel('level / arbitrary units')
        return

    def plot_horn_action(self):
        '''
        plot the inductance curve from the horn switch
        '''
        now_str = dt.datetime.utcnow().strftime(self.date_fmt)
        if self.header['IS_GOOD']==1:
            goodbad = 'good'
        else:
            goodbad = 'bad'
        if self.header['HORN_ID'] is not None:
            hornid = self.header['HORN_ID']
        else:
            hornid = 'unknown'
        if self.header['CHANNEL'] is not None:
            channel = self.header['CHANNEL']
        else:
            channel = 'unknown'
        
        infotxt = 'Horn %s is %s (measured on channel %s)' % (hornid,goodbad,channel)
        msg = '%s: %s' % (now_str,infotxt)
        
        if self.plot_type=='ascii':
            gp.plot(self.dat, terminal="dumb", _with="points pointtype '+'", unset="grid", title=msg )
            return
        
        self.ax.plot(self.dat,label=msg)
        self.ax.legend()
        plt.pause(0.01)
    
        return



    def write_horn_fits(self,tstamp):
        '''
        write the inductance curve to FITS file
        '''
        npts = len(self.dat)
        startTime = dt.datetime.fromtimestamp(tstamp)
        file_ctr = 0
        outfile = 'hornswitch_%i_%s.fits' % (file_ctr,startTime.strftime('%Y%m%dT%H%M%S'))
        while os.path.isfile(outfile):
            file_ctr += 1
            outfile = 'hornswitch_%i_%s.fits' % (file_ctr,startTime.strftime('%Y%m%dT%H%M%S'))

        records=np.recarray(formats='>i4',names='amplitude',shape=(npts))
        records.amplitude = self.dat

        # FITS primary header
        prihdr=fits.Header()
        prihdr['INSTRUME'] = 'QUBIC'
        prihdr['EXTNAME']  = 'HORNSWITCH'
        prihdr['DATE-OBS'] = startTime.strftime('%Y-%m-%d %H:%M:%S.%f UT')
        for key in self.header.keys():
            prihdr[key] = self.header[key]
        prihdu = fits.PrimaryHDU(header=prihdr)

        cols  = fits.FITS_rec(records)
    
        hdu1  = fits.BinTableHDU.from_columns(cols)
        hdu1.header['INSTRUME'] = 'QUBIC'
        hdu1.header['EXTNAME'] = 'HORNSWITCH'
        hdu1.header['DATE-OBS'] = startTime.strftime('%Y-%m-%d %H:%M:%S.%f UT')
        for key in self.header.keys():
            hdu1.header[key] = self.header[key]
        
        hdulist = [prihdu,hdu1]
        thdulist = fits.HDUList(hdulist)
        thdulist.writeto(outfile,overwrite=True)
        thdulist.close()
        print('saved file: %s' % outfile)
        return outfile


    ### does this work?
    def send_to_horns(self,horn):
        '''
        command the horn to open/close
        ... this is under development!!
        '''

        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.2)
        s.bind(('192.168.2.1',1700))
        msg='close %i\r\nswread %i\r\n' % (horn,horn)
        s.sendto(msg, (receiver, 1700))
        return


    def recent_files(self):
        '''
        find the most recent saved event
        this only looks in the current directory
        '''
        
        print('looking in current directory for horn switch files...')
        pattern = 'hornswitch_0_????????T??????.fits'
        files = glob(pattern)
        if not files:
            print('no files found.')
            return None
        
        files.sort()
        f0 = files[-1]

        # check if this is a double closure event
        endpattern = f0.split('_')[-1].replace('.fits','')
        pattern = 'hornswitch_?_%s?.fits' % endpattern[:-1] # nearest microsecond
        files = glob(pattern)
        files.sort()
        print('files found:')
        for f in files:
            print('   %s' % f)
        return files

    def plot_saved_event(self,files):
        '''
        plot the inductance curved of a saved event
        '''
        if files is None: return

        self.setup_horn_plot()

        for f in files:
            h = fits.open(f)
            if len(h)<>2\
               or 'INSTRUME' not in h[1].header.keys()\
               or h[1].header['INSTRUME']<>'QUBIC'\
               or 'EXTNAME' not in h[1].header.keys()\
               or h[1].header['EXTNAME']<>'HORNSWITCH':
                print('not a horn switch fits file: %s' % f)
                h.close()
                continue
            
            dat = h[1].data.field(0)
            obsdate = str2dt(h[1].header['DATE-OBS'])
            obsdate_str = dt.datetime.utcnow().strftime(self.date_fmt)

            keys = h[1].header.keys()
            if 'IS_GOOD' in keys:
                if h[1].header['IS_GOOD']==1:
                    goodbad = 'good'
                else:
                    goodbad = 'bad'
            else:
                goodbad = 'unknown'
                
            if 'HORN_ID' in keys:
                hornid = h[1].header['HORN_ID']
            else:
                hornid = 'unknown'
                
            if 'CHANNEL' in keys:
                channel = h[1].header['CHANNEL']
            else:
                channel = 'unknown'
        
            infotxt = 'Horn %s is %s (measured on channel %s)' % (hornid,goodbad,channel)
            msg = '%s: %s' % (obsdate_str,infotxt)
            h.close()
            
            if self.plot_type=='ascii':
                gp.plot(self.dat, terminal="dumb", _with="points pointtype '+'", unset="grid", title=msg )
                continue

            self.ax.plot(dat,label=msg)
            self.ax.legend()
        return


    

            
            
    
