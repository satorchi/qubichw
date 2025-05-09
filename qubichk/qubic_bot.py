'''
$Id: qubic_bot.py
$auth: Manuel Gonzalez <manuel.gonzalez@ib.edu.ar>
$created: Tues 12 June 2018

$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

This is the QUBIC Telegram bot
https://web.telegram.org/#/im?p=@QUBIC_bot

'''
import sys,os,re,time,inspect,urllib
import datetime as dt
from glob import glob
import numpy as np

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

from satorchipy.datefunctions import str2dt
from qubichw.calsource_configuration_manager import calsource_configuration_manager
from qubichk.hk_verify import check_compressors,check_diskspace

from qubichk.send_telegram import get_botId,get_TelegramAddresses, get_alarm_recipients
from qubichk.utilities import get_fullpath
from qubichk.ups import get_ups_info
#from qubichk.platform import get_position
from qubichk.utilities import shellcommand

class dummy_bot:
    '''
    a dummy bot for testing
    '''
    def __init__(self):
        return

    def sendMessage(self,chat_id,answer):
        print('TESTMODE: Bot sent:\n\n%s' % answer)
        return

    def sendPhoto(self,chat_id,photo):
        print('TESTMODE: Bot sent photo')
        return 

    def message_loop(self,botfunc, run_forever=False):
        print('TESTMODE: Bot running loop')
        cmd=''
        msg={}
        msg['chat']={}
        msg['chat']['id']=0
        for arg in sys.argv[1:]:
            if arg.find('--test')<0:cmd+=' '+arg
        msg['text']=cmd.strip()
        botfunc(msg)
        return


class qubic_bot :
    '''
    a class to send QUBIC housekeeping information via Telegram
    '''

    def __init__(self,test=False,idfile=None):
        self.TESTMODE=test
        self.botId=None
        self.bot=None
        self.timestamp_factor = 1e-3 # on and before 20181217
        self.timestamp_factor = 1

        self.hktypes = ['TEMPERATURE','AVS47_1','AVS47_2','HEATER','MHS','PRESSURE']
        self.nHeaters = 6
        self.nMHS = 2
        self.nPressure = 1

        self.labelsize = 20
        
        # this list could be generated with inspect...
        self.commands = {'/start': self.start,
                         '/help': self.ayuda,
                         '/temp': self.temp_read_hk,
                         '/tempall': self.tempall,
                         '/heaters': self.read_heaters,
                         '/pressure': self.read_pressure,
                         '/mech': self.read_mech,
                         '/calsource': self.calsource,
                         '/photo': self.photo1,
                         '/photo2': self.photo2,
                         '/photo3': self.cam26,
                         '/photo4': self.cam27,
                         '/plot' : self.plot,
                         '/list' : self.list_channels,
                         '/entropy': self.entropy_temp,
                         '/entropy_plotall': self.entropy_plotall,
                         '/plot300mkzoom': self.entropy_plot300mKzoom,
                         '/plot300mk': self.entropy_plot300mK,
                         '/plot1k': self.entropy_plot1K,
                         '/ip': self.ip,
                         '/pt': self.pt,
                         '/diskspace': self.diskspace,
                         '/ups': self.ups,
                         '/subscribe': self.subscribe,
                         '/unsubscribe':self.unsubscribe,
                         '/position': self.position
                         }


        self.temperature_headings = ['40K filters',
                                     '40K sd',
                                     '40K sr',
                                     'PT2 s1',
                                     'PT1 s1',
                                     '4K filters',
                                     'HWP1',
                                     'HWP2',
                                     '4K sd',
                                     '4K PT2 CH',
                                     'PT1 s2',
                                     'PT2 s2',
                                     '300mK-4CP-D-1',
                                     '300mK-4HS-D-1',
                                     '300mK-3CP-D-1',
                                     '300mK-3HS-D-1',
                                     '1K-4HS-D-1',
                                     '1K-4CP-D-1']

        self._assign_entropy_labels()
        self._assign_heater_labels()

        self.temperature_display_order = [4, 3, 10, 11, 9, 6, 7, 0, 1, 2, 5, 8, 12, 13, 14, 15, 16, 17]
        temperature_heading_len = [ len(val) for val in self.temperature_headings ]
        self.temperature_heading_maxlen = max(temperature_heading_len)
        self.nTemperatures = len(self.temperature_headings)

        # for plotting all temperatures
        self.allTemperatures = {}
        for idx in range(2):
            avs = 'AVS47_%i' % (idx+1)
            self.allTemperatures[avs]=[]
            for ch in range(8):
                if self.entropy_channel_title[avs][ch].find('Touch')<0:
                    self.allTemperatures[avs].append(ch)
        self.allTemperatures['TEMPERATURE'] = range(1, self.nTemperatures+1)

        if 'HOME' in os.environ:
            homedir = os.environ['HOME']
        else:
            homedir = '/home/qubic'
        self.hk_dir = homedir+'/data/temperature/broadcast'

        # this is not used since we implemented HK socket broadcasting 20181212
        self.temperature_log_dir = homedir+'/data/temperature/data/log_cryo/dirfile_cryo_current'

        self.time_fmt='%Y-%m-%d %H:%M:%S UT'
        
        self._init_args()
        self.botId = get_botId()
        if self.botId is not None:
            self._init_bot()
            self._begin_bot()
            
        return None

    def _init_bot(self):
        '''
        initialize the Telegram bot.  Use the dummy bot if we're just testing
        '''
        if self.TESTMODE:
            print('running in test mode')
            self.bot=dummy_bot()
            self.chat_id=0            
        else:
            import telepot
            self.bot = telepot.Bot(self.botId)
            self.bot.getMe()
            
        return

    def _begin_bot(self):
        '''
        start the listening loop
        '''
        self.bot.message_loop(self._respuesta, run_forever=True)
        
        return

    def _init_args(self):
        '''
        setup the default arguments
        '''
        self.args={}
        self.args['YMIN']=None
        self.args['YMAX']=None
        self.args['DMIN']=None
        self.args['DMAX']=None
        self.args['LOG']=False
        for key in self.hktypes:
            self.args[key] = []
        
        return

    def _send_message(self,msg):
        '''
        send a message from the bot
        '''
        if self.bot is None:
            print('bot not configured.  message not sent: %s' % msg)
            return
        
        self.bot.sendMessage(self.chat_id,msg)
        return

    def _send_photo(self,image):
        '''
        send an image from the bot
        '''
        if self.bot is None:
            print('ERROR!  Bot is not initialized.  Photo not sent.')
            return
        self.bot.sendPhoto(self.chat_id,image)
        return

    def start(self):
        '''
        a nice message to send to first time users
        '''
        msg="Hi, I'm the Telegram bot of the QUBIC experiment.  This is the list of the available commands:"
        self._send_message(msg)
        self.ayuda()
        return

    def ayuda(self):
        '''
        some help:  This is a list of commands
        '''
        msg = '\n'.join(self.commands.keys())
        msg += '\n\n'
        self._send_message(msg)
        self.plothelp()
        return

    def temp_read_hk(self):
        '''
        read temperatures from the Housekeeping broadcast
        '''
        latest_date = dt.datetime.utcfromtimestamp(0)
        fmt_str = '\n%%%is:  %%7.3fK' % self.temperature_heading_maxlen
        answer = 'Temperatures:'
        for ch_idx in self.temperature_display_order:
            basename = 'TEMPERATURE%02i.txt' % (ch_idx+1)
            fullname = '%s/%s' % (self.hk_dir,basename)
            if not os.path.isfile(fullname):
                answer += '\n%s:\tno data' % self.temperature_headings[ch_idx]
            
            else:
                h = open(fullname,'rb')
                nbytes = h.seek(0,os.SEEK_END)
                if nbytes < 35:
                    h.close()
                    answer += '\n%s:\tinsufficient data' % self.temperature_headings[ch_idx]
                else:
                    h.seek(-35,os.SEEK_END)
                    lines = h.read().decode().split('\n')
                    h.close()
                    lastline = lines[-2]
                    cols = lastline.split()
                    tstamp = self.timestamp_factor*float(cols[0])
                    reading_date = dt.datetime.utcfromtimestamp(tstamp)
                    if reading_date > latest_date:
                        latest_date = reading_date
                    reading = eval(cols[1])
                    answer += fmt_str % (self.temperature_headings[ch_idx],reading)

        answer += '\n\nTime: %s' % latest_date.strftime(self.time_fmt)    
        self._send_message(answer)
        return

    def temp_hk_data(self,ch=1):
        '''
        return the date,temperature data from the Housekeeping broadcast
        '''
        basename = 'TEMPERATURE%02i.txt' % ch
        fullname = '%s/%s' % (self.hk_dir,basename)
        if not os.path.isfile(fullname):
            return None,None

        h = open(fullname,'r')
        lines = h.read().split('\n')
        h.close()
        del(lines[-1])
        t=[]
        v=[]
        for line in lines:
            cols = line.split()
            try:
                tstamp = self.timestamp_factor*float(cols[0])
                reading_date = dt.datetime.utcfromtimestamp(tstamp)
                reading = eval(cols[1])
                t.append(reading_date)
                v.append(reading)
            except:
                pass
        return t,v

    def _assign_heater_labels(self):
        ''' read user supplied labels corresponding to HEATER1, HEATER2, etc
        '''
        # default labels
        self.heater_label = {}
        for idx in range(self.nHeaters):
            label = 'HEATER%i' % (idx+1)
            self.heater_label[label] = label

        # read the powersupply config file
        if 'HOME' in os.environ.keys():
            homedir = os.environ['HOME']
        else:
            homedir = os.path.curdir
        
        configfile = homedir + os.sep + 'powersupply.conf'
        if not os.path.isfile(configfile):
            return
        
        h = open(configfile,'r')
        lines = h.read().split('\n')
        for line in lines:
            match = re.match('^(HEATER.*): (.*)',line)
            if match:
                key = match.groups()[0]
                label = match.groups()[1]
                self.heater_label[key] = label
            
        return
    

    def read_heaters(self):
        '''
        read the status of the heaters (power supplies)
        '''
        latest_date = dt.datetime.utcfromtimestamp(0)
        fmt_str = '\n%20s:  %7.3f %s %s'
        units = ['V','mA']
        answer = 'Heaters:'
        for idx in range(self.nHeaters):
            basename = 'HEATER%i' % (idx+1)
            label = basename
            if basename in self.heater_label.keys():
                label = '%8s - %9s' % (basename,self.heater_label[basename])
            for meastype_idx,meastype in enumerate(['Volt','Amp']):
                fullname = '%s/%s_%s.txt' % (self.hk_dir,basename,meastype)
                if not os.path.isfile(fullname):
                    continue
        
                h = open(fullname,'r')
                lines = h.read().split('\n')
                h.close()
                lastline = lines[-2]
                cols = lastline.split()
                tstamp = self.timestamp_factor*float(cols[0])
                reading_date = dt.datetime.utcfromtimestamp(tstamp)
                if reading_date > latest_date:
                    latest_date = reading_date
                reading = eval(cols[1])
                if len(cols)==3: status = cols[2]
                else: status = ''
                answer += fmt_str % (label,reading,units[meastype_idx],status)
            answer += '\n'

        answer += 'Time: %s' % latest_date.strftime(self.time_fmt)    
        self._send_message(answer)
        return

    def heater_hk_data(self,ch):
        '''
        return the date,power data from the heaters (power supplies)
        '''
        basename_volt = 'HEATER%i_Volt.txt' % ch
        fullname_volt = '%s/%s' % (self.hk_dir,basename_volt)
        if not os.path.isfile(fullname_volt):
            print('Could not find file: %s' % fullname_volt)
            return None,None
        basename_amp = 'HEATER%i_Amp.txt' % ch
        fullname_amp = '%s/%s' % (self.hk_dir,basename_amp)
        if not os.path.isfile(fullname_amp):
            print('Could not find file: %s' % fullname_amp)
            return None,None


        #print('Reading Heater files:\n  %s\n  %s' % (fullname_volt,fullname_amp))

        power = []
        # read voltages
        h = open(fullname_volt,'r')
        lines = h.read().split('\n')
        h.close()
        del(lines[-1])
        
        t_volt=[]
        volt=[]
        for line in lines:
            cols = line.split()
            try:
                tstamp = self.timestamp_factor*float(cols[0])
                t_volt.append(tstamp)
                reading = eval(cols[1])
                volt.append(reading)
                power.append(-1)
                if len(cols)==3:
                    status = cols[2]
                    if status=='OFF':
                        volt[-1] = 0.0
                        power[-1] = 0.0
            except:
                print("Couldn't interpret data:  %s" % line)

        # read currents
        h = open(fullname_amp,'r')
        lines = h.read().split('\n')
        h.close()
        del(lines[-1])

        t_amp=[]
        amp=[]
        for line in lines:
            cols = line.split()
            try:
                tstamp = self.timestamp_factor*float(cols[0])
                t_amp.append(tstamp)
                reading = eval(cols[1])
                amp.append(reading)
                if len(cols)==3:
                    status = cols[2]
                    if status=='OFF':
                        amp[-1]=0.0
            except:
                #print("Couldn't interpret data:  %s" % line)
                pass
        amp = np.array(amp)


        t = np.array(t_volt)
        dates = []
        for idx,tstamp in enumerate(t):
            dates.append(dt.datetime.utcfromtimestamp(tstamp))
            p = power[idx]
            if p==-1:
                v = volt[idx]
                i_indexes = np.where( (t>tstamp-1)*(t<tstamp+1) )
                #print('indexes = %s' % i_indexes)
                i_avg = amp[i_indexes].mean()
                power[idx] = i_avg*v                                         
        
        return dates,power

    
    def read_mech(self):
        '''
        read the mechanical heat switch positions
        '''
        latest_date = dt.datetime.utcfromtimestamp(0)
        fmt_str = '\n%7s:  %8i'
        answer = 'Mechanical Heat Switch Positions:\n'
        for idx in range(2):
            basename = 'MHS%i' % (idx+1)
            fullname = '%s/%s.txt' % (self.hk_dir,basename)
            if not os.path.isfile(fullname):
                continue
        
            h = open(fullname,'r')
            lines = h.read().split('\n')
            h.close()
            lastline = lines[-2]
            cols = lastline.split()
            tstamp = self.timestamp_factor*float(cols[0])
            reading_date = dt.datetime.utcfromtimestamp(tstamp)
            if reading_date > latest_date:
                latest_date = reading_date
            reading = eval(cols[1])
            answer += fmt_str % (basename,reading)

        answer += '\n\nTime: %s' % latest_date.strftime(self.time_fmt)    
        self._send_message(answer)
        return
    
    def read_pressure(self):
        '''
        read the pressure
        '''
        latest_date = dt.datetime.utcfromtimestamp(0)
        fmt_str = '\n%10s:  %10.3e mbar'
        answer = 'Pressure:\n'

        idx = 0
        basename = 'PRESSURE%i' % (idx+1)
        fullname = '%s/%s.txt' % (self.hk_dir,basename)
        if not os.path.isfile(fullname):
            answer = 'No pressure.'
            answer += '\n\nTime: %s' % latest_date.strftime(self.time_fmt)    
            self._send_message(answer)
            return
        
        h = open(fullname,'r')
        lines = h.read().split('\n')
        h.close()
        lastline = lines[-2]
        cols = lastline.split()
        tstamp = self.timestamp_factor*float(cols[0])
        reading_date = dt.datetime.utcfromtimestamp(tstamp)
        if reading_date > latest_date:
            latest_date = reading_date
        reading = eval(cols[1])
        answer += fmt_str % (basename,reading)

        answer += '\n\nTime: %s' % latest_date.strftime(self.time_fmt)    
        self._send_message(answer)
        return

    def pressure_hk_data(self,ch=1):
        '''
        return the data,pressure data
        '''
        basename = 'PRESSURE%i.txt' % ch
        fullname = '%s/%s' % (self.hk_dir,basename)
        if not os.path.isfile(fullname):
            return None,None

        h = open(fullname,'r')
        lines = h.read().split('\n')
        h.close()
        del(lines[-1])
        t=[]
        v=[]
        for line in lines:
            cols = line.split()
            try:
                tstamp = self.timestamp_factor*float(cols[0])
                reading_date = dt.datetime.utcfromtimestamp(tstamp)
                reading = eval(cols[1])
                t.append(reading_date)
                v.append(reading)
            except:
                pass
        return t,v
    
    def photo(self,camnum):
        '''
        wrapper for webcams
        '''
        if camnum==1:return self.photo1()
        if camnum==2:return self.photo2()
        if camnum==3:return self.webcam('cam26')
        if camnum==4:return self.webcam('cam27')
        
        return
    

    def photo1(self):
        '''
        take a picture of the APC QUBIC Integration Lab
        with the webcam near the calibration source
        '''
        cmd='ssh pigps ./snapshot.sh'
        out,err = shellcommand(cmd)
        cmd='scp -p pigps:webcamshot.jpg .'
        out,err = shellcommand(cmd)
        with open('webcamshot.jpg','rb') as photo:
            if photo is not None: self._send_photo(photo)
        return

    def photo2(self):
        '''
        take a picture of the APC QUBIC Integration Lab
        with the webcam on the electronics rack
        '''
        cmd='ssh pitemps ./snapshot.sh'
        out,err = shellcommand(cmd)
        cmd='scp -p pitemps:webcamshot.jpg .'
        out,err = shellcommand(cmd)
        with open('webcamshot.jpg','rb') as photo:
            if photo is not None: self._send_photo(photo)
        return

    def webcam(self,camname):
        '''
        take a picture of the APC QUBIC Integration Lab
        with webcam26 or webcam27
        '''
        if camname=='cam26':
            camurl = 'http://192.168.2.26:81/snapshot.cgi?user=admin&pwd=coucou'
        else:
            camurl = 'http://192.168.2.27:81/snapshot.cgi?user=admin&pwd='
        
        requester = urllib.request.Request(camurl)
        imgfile = urllib.request.urlopen(requester)
        self._send_photo(imgfile)
        imgfile.close()
        return

    def cam26(self):
        '''
        take a picture of the APC QUBIC Integration Lab
        with webcam26
        '''
        return self.webcam('cam26')
    
    def cam27(self):
        '''
        take a picture of the APC QUBIC Integration Lab
        with webcam27
        '''
        return self.webcam('cam27')
    
    def entropy_latest_temperature_dir(self):
        '''
        find the location of the most recent temperature data
        '''
        entropy_dir='/entropy/logs'
    
        if not os.path.exists(entropy_dir):
            answer='Cannot read the temperatures on Entropy'
            self._send_message(answer)
            return None

        dlist=[]
        for r,d,f in os.walk(entropy_dir):
            if r!=entropy_dir:
                dlist.append(r)

        dlist.sort(key=os.path.getmtime)
        tempdir=dlist[-1]
        return tempdir


    def _assign_entropy_labels(self):
        '''
        read temperature labels from the Entropy Windows machine, shared by Samba
        '''
        print('assigning entropy labels')
        # default labels
        self.entropy_channel_title={}
        self.entropy_channel_title['AVS47_1']=[]
        self.entropy_channel_title['AVS47_2']=[]
        for ch in range(8):
            for avs in ['AVS47_1','AVS47_2']:
                default_label='%s ch%i' % (avs,ch)
                self.entropy_channel_title[avs].append(default_label)

        # check if we can read the entropy data directory
        tempdir=self.entropy_latest_temperature_dir()
        if tempdir is None:return None
                
        # read the configured labels
        self.entropy_nchannels=0
        filelist=glob(tempdir+'/*')
        match_str = '.* AVS47 (AVS47_[12]) Ch ([0-7]) '
        for f in filelist:
            chan_str = re.sub('\.log','',os.path.basename(f))
            match = re.match(match_str,chan_str)
            chan_str = re.sub(match_str,'',chan_str)
            if match:
                avs=match.group(1)
                ch=eval(match.group(2))
                self.entropy_channel_title[avs][ch]=chan_str
                self.entropy_nchannels+=1
                                

        # debug message
        for avs in self.entropy_channel_title.keys():
            print(avs)
            for ttl in self.entropy_channel_title[avs]:
                print(ttl)
        return
    
    def entropy_temp(self):
        '''                                                                                                      
        read temperatures from the Entropy Windows machine, shared by Samba
        '''
        tempdir=self.entropy_latest_temperature_dir()
        if tempdir is None:return tempdir

        latest_date = dt.datetime.utcfromtimestamp(0)
    
        answer_list = []
        filelist=glob(tempdir+'/*')
        for f in filelist:
            chan_str = re.sub('\.log','',os.path.basename(f))
            chan_str = re.sub('.* AVS47 AVS47_[12] Ch [0-7] ','',chan_str)
            h = open(f,'rb')
            dat = h.read()
            h.close()
            del(h)
            try:
                lines = dat.decode('iso-8859-1').split('\n')
            except:  # hack in case iso-8859-1 is not correct
                lines = str(dat).replace('\\t','\t').replace('\\r','').split('\\n')
                            

            for line in lines:
                if line.find('#Log session timestamp:')==0:
                    # get start time from header
                    tstart_str=line.replace('#Log session timestamp:','')
                    try:
                        tstart=eval(tstart_str)*1e-3 
                    except:
                        tstart=-1
                    break
        
            lastline=lines[-2]
            cols=lastline.split()
            val=float(cols[1])
            if len(cols)==3:
                if val<1:
                    fmt_str = '%s : %.1f mK'
                    val *= 1000
                else:
                    fmt_str = '%s : %.3f K'
                tempans=fmt_str % (chan_str,val)
            else:
                tempans='%s : %.4f Ohm' % (chan_str,val)        

            tstamp = 1e-3*eval(cols[0]) + tstart
            reading_date = dt.datetime.utcfromtimestamp(tstamp)
            if reading_date > latest_date:
                latest_date = reading_date

            if tempans.find('MCST3601')<0:
                answer_list.append('[%s]  %s' % (reading_date.strftime(self.time_fmt),tempans))
                

            
        now='\nTime: %s' % latest_date.strftime(self.time_fmt)
        answer_list.append(now)

        answer = '\n'.join(answer_list)
    
        self._send_message(answer)
        return answer
        
    def read_entropy_logfile(self,filename):
        '''
        read a temperature log file produced by Entropy
        '''
        if not os.path.exists(filename):
            print('file not found: %s' % filename)
            return None,None
        if not os.path.isfile(filename):
            print('this is not a file: %s' % filename)
            return None,None

        h=open(filename,'rb')
        dat = h.read()
        h.close()
        try:
            lines = dat.decode('iso-8859-1').split('\n')
        except:  # hack in case iso-8859-1 is not correct
            lines = str(dat).replace('\\t','\t').replace('\\r','').split('\\n')

        # go through the lines
        t=[]
        val=[]
        for line in lines:
            if line.find('#')!=0:
                cols=line.split()
                try:
                    tt=eval(cols[0])*1e-3
                    yy=eval(cols[1])
                    t.append(tt)
                    val.append(yy)
                
                except:
                    #print('DEBUG: unable to interpret: %s' % line)
                    pass
            elif line.find('#Log session timestamp:')==0:
                # get start time from header
                tstart_str=line.replace('#Log session timestamp:','')
                try:
                    tstart=eval(tstart_str)*1e-3
                except:
                    tstart=-1

        #print('DEBUG: tstart = %f' % tstart)
        t=np.array(t)
        #print(t)
        val=np.array(val)
        #print(val)
        tdate=[]
        if tstart>0:
            t+=tstart
            for tstamp in t:
                tdate.append(dt.datetime.utcfromtimestamp(tstamp))
        else:
            tdate=t

        return tdate,val

    def tempall(self):
        '''
        print out all the temperatures
        '''
        self.entropy_temp()
        self.temp_read_hk()
        return

    
    def plot_temperature(self,t,v,title,dmin=None,dmax=None,Tmin=None,Tmax=None,logscale=False):
        '''
        make a quick plot of the temperature cooldown/warmup
        '''

        plt.ioff()
        fig=plt.figure(figsize=(20.48,7.68))
        plt.plot(t,v,ls='none',marker='D')
        ax=fig.axes[0]
        if Tmin is None:Tmin=min(v)
        if Tmax is None:Tmax=max(v)
        if dmin is None:dmin=t[0]
        if dmax is None:dmax=t[-1]
        ax.set_ylim(Tmin,Tmax)
        ax.set_xlim(dmin,dmax)
        
        
        ax.set_xlabel('date',fontsize=self.labelsize)
        ax.set_ylabel('temperature / K',fontsize=self.labelsize)
        ax.tick_params(labelsize=self.labelsize)
        fig.suptitle(title,fontsize=self.labelsize)
        savefig_fmt='png'
        fig.savefig('temperature_plot.'+savefig_fmt,format=savefig_fmt,dpi=100,bbox_inches='tight')
    
        plt.close()
        return

    def entropy_plot_channel(self,controller=1,channel=1,dmin=None,dmax=None,Tmin=None,Tmax=None,logscale=False):
        '''
        plot a given channel
        '''
        tempdir=self.entropy_latest_temperature_dir()
        if tempdir is None:return None

        filename=''
        find_str='.* AVS47_%i Ch (%i)' % (controller,channel)

        filelist=glob(tempdir+'/*')
        for f in filelist:
            match=re.match(find_str,f)
            if match:
                filename=f
                break

        avs = 'AVS47_%i' % controller
        print('DEBUG: filename=%s' % filename)
        t,v=self.read_entropy_logfile(filename)
        if t is None:
            answer='No MACRT temperatures on Entropy'
            self._send_message(answer)
            return answer

        result=self.plot_temperature(t,v,self.entropy_channel_title[avs][channel],
                                     dmin=dmin,dmax=dmax,Tmin=Tmin,Tmax=Tmax,logscale=logscale)
        with open('temperature_plot.png','rb') as plot:
            self.bot.sendPhoto(self.chat_id,plot)
        return

    def entropy_channel_data(self,controller=1,channel=1):
        '''
        get the date,temperature data from one of the Entropy temperature sensors
        '''
        tempdir=self.entropy_latest_temperature_dir()
        if tempdir is None:return None,None

        filename=''
        find_str='.* AVS47_%i Ch (%i)' % (controller,channel)

        filelist=glob(tempdir+'/*')
        for f in filelist:
            match=re.match(find_str,f)
            if match:
                filename=f
                break

        t,v = self.read_entropy_logfile(filename)
        return t,v
        


    def entropy_plot1K(self):
        '''
        make a plot of the 1K stage and send it via telegram
        '''
        return self.entropy_plot_channel(channel=1)

    def entropy_plot300mK(self):
        '''
        plot the 0.3K stage and send it via telegram
        '''
        return self.entropy_plot_channel(channel=2)

    def entropy_plot300mKzoom(self):
        '''
        plot the last hour of 300mK data
        '''
        tempdir=self.entropy_latest_temperature_dir()
        if tempdir is None:return None
        channel=2
        filename=''
        find_str='.*(AVS47_[12]) Ch (%i)' % channel
        filelist=glob(tempdir+'/*')
        for f in filelist:
            match=re.match(find_str,f)
            if match:
                filename=f
                avs = match.groups()[0]
                break


        t,v=self.read_entropy_logfile(filename)
        if t is None:
            answer='No AVS47 temperatures on Entropy'
            self._send_message(answer)
            return answer

        dmax=t[-1]
        dmin=dmax-dt.timedelta(minutes=60)
        for idx,dd in enumerate(t):
            if dd>dmin:
                imin=idx
                break
        Tmin=min(v[imin:])
        Tmax=max(v[imin:])
    
        result=self.plot_temperature(t,v,self.entropy_channel_title[avs][channel],dmin,dmax,Tmin,Tmax)
        with open('temperature_plot.png','rb') as plot:
            self._send_photo(plot)
        return

    def entropy_plotall(self,Tmin=None,Tmax=None):
        '''
        plot all temperatures available from entropy
        '''
        tempdir=self.entropy_latest_temperature_dir()
        if tempdir is None:return tempdir

        plt.ioff()
        fig=plt.figure(figsize=(20.48,7.68))

        filelist=glob(tempdir+'/*')
        Tminlist=[]
        Tmaxlist=[]
        for f in filelist:
            print(f)
            find_str='.*(AVS47_[12]) Ch ([0-%i])' % (self.entropy_nchannels-1)
            match=re.match(find_str,f)
            if match:
                ch=eval(match.groups()[1])
                t,v=self.read_entropy_logfile(f)
                Tminlist.append(min(v))
                Tmaxlist.append(max(v))
                avs = match.groups()[0]
                if t is not None:plt.plot(t,v,ls='none',marker='D',label=self.entropy_channel_title[avs][ch])
        if Tmin is None:
            Tmin = min(Tminlist)
        if Tmax is None:
            Tmax = max(Tmaxlist)
        ax=fig.axes[0]
        ax.set_ylim((Tmin,Tmax))
        ax.set_xlabel('date',fontsize=self.labelsize)
        ax.set_ylabel('temperature / K',fontsize=self.labelsize)
        ax.tick_params(labelsize=self.labelsize)
        fig.suptitle('Temperatures from the AVS47',fontsize=self.labelsize)
        plt.legend(fontsize=self.labelsize)
        fig.savefig('temperature_plot.png',format='png',dpi=100,bbox_inches='tight')
        plt.close()
        with open('temperature_plot.png','rb') as plot:
            self._send_photo(plot)
        return

    def plothelp(self):
        '''
        give some info about how to use the plot function
        '''
        msg =  'Help for the plot function: Plot Housekeeping data.'
        msg += '\nThis function can be used to plot a selection of housekeeping data.'
        msg += '\n - The default behaviour (no arguments) is to make a plot of all temperatures.'
        msg += '\n - The channel list is a comma separated list of channels.'
        msg += '\n - dates should be given in ISO format, for example: 2019-01-15T20:18:00'
        msg += '\n\nusage:  Plot [PRESSURE] [T=<channel list>]'
        msg += ' [AVS1=<channel list>] [AVS2=<channel list>] [DMIN=<start date>] [DMAX=<end date>]'
        msg += ' [MIN=<min value>] [MAX=<max value>] [LOG]'
        msg += '\n\n to get a list of temperature labels, send the command "list"'
        msg += '\n\n Example:  plot temperature diodes 1,3,4 and AVS47 controller 1 channel 3 starting from 25 October, 2019 at 15hr.'
        msg += '\n    plot T=1,3,4 avs1=3 dmin=2019-10-25T15:00:00'
        self._send_message(msg)
        return
    
    def plot(self):
        '''
        this is a generic plot using the parsed arguments
        '''
        if self.args is not None:
            print('I found the following keys:')
            for key in self.args.keys():
                print('%s: %s' % (key,self.args[key]))
            if 'HELP' in self.args.keys():
                return self.plothelp()                
        else:
            # nothing selected, return the help.  Plot all takes a lot of  time, so avoid it.
            print("I didn't find any arguments")
            return self.plothelp()
            

        something2plot = False
        plt.ioff()
        fig=plt.figure(figsize=(20.48,7.68))
        tmin_list=[]
        tmax_list=[]
        dmin_list=[]
        dmax_list=[]
        
        # plot temperature diodes
        for ch in self.args['TEMPERATURE']:
            ch_idx = ch-1
            t,v=self.temp_hk_data(ch)
            if (t is not None) and (v is not None):
                something2plot = True
                channel_label=self.temperature_headings[ch_idx]
                plt.plot(t,v,ls='none',marker='D',label=channel_label)
                tmax_list.append(max(v))
                tmin_list.append(min(v))
                dmax_list.append(max(t))
                dmin_list.append(min(t))
        if self.args['TEMPERATURE']:
            ylabel = 'temperature / K'
            ttl = 'Temperatures'

        # plot AVS47 temperatures
        self._assign_entropy_labels()
        for controller in [1,2]:
            avs = 'AVS47_%i' % controller
            if self.args[avs]:
                ylabel = 'temperature / K'
                ttl = 'Temperatures'
            for ch in self.args[avs]:
                t,v = self.entropy_channel_data(controller,ch)
                if (t is not None) and (v is not None):
                    something2plot = True
                    entropy_label=self.entropy_channel_title[avs][ch]
                    plt.plot(t,v,ls='none',marker='D',label=entropy_label)                
                    tmax_list.append(max(v))
                    tmin_list.append(min(v))
                    dmax_list.append(max(t))
                    dmin_list.append(min(t))

        # plot heater power
        for ch in self.args['HEATER']:
            idx = ch-1
            t,v=self.heater_hk_data(ch)
            if (t is not None) and (v is not None):
                something2plot = True
                channel_label='HEATER%i' % ch
                plt.plot(t,v,ls='none',marker='D',label=channel_label)
                tmax_list.append(max(v))
                tmin_list.append(min(v))
                dmax_list.append(max(t))
                dmin_list.append(min(t))
        if self.args['HEATER']:
            ylabel = 'power / mW'
            ttl = 'Heater power'

        # plot pressure
        for ch in self.args['PRESSURE']:
            t,v = self.pressure_hk_data(ch)
            if (t is not None) and (v is not None):
                something2plot = True
                channel_label='PRESSURE%i' % ch
                plt.plot(t,v,ls='none',marker='D',label=channel_label)
                tmax_list.append(max(v))
                tmin_list.append(min(v))
                dmax_list.append(max(t))
                dmin_list.append(min(t))
        if self.args['PRESSURE']:
            ylabel = 'pressure / mbar'
            ttl = 'Pressure'

        if not something2plot:
            msg = 'Sorry, your argument list resulted in no plot.  Are you sure about the channel numbers?'
            self._send_message(msg)
            return self.plothelp()

        Tmin=min(tmin_list)
        Tmax=max(tmax_list)
        if self.args['YMIN'] is not None:
            Tmin=self.args['YMIN']
        if self.args['YMAX'] is not None:
            Tmax=self.args['YMAX']
            
        dmin=min(dmin_list)
        dmax=max(dmax_list)
        if self.args['DMIN'] is not None:
            dmin=self.args['DMIN']
        if self.args['DMAX'] is not None:
            dmax=self.args['DMAX']
            
        ax=fig.axes[0]
        ax.set_xlim((dmin,dmax))
        ax.set_ylim((Tmin,Tmax))
        ax.set_xlabel('date',fontsize=self.labelsize)
        plt.xticks(fontsize=self.labelsize)
        ax.set_ylabel(ylabel,fontsize=self.labelsize)
        plt.yticks(fontsize=self.labelsize)
        fig.suptitle(ttl,fontsize=self.labelsize)
        plt.legend(fontsize=self.labelsize)
        
        plt.grid()
        if self.args['LOG']: plt.yscale("log")
        fig.savefig('hk_plot.png',format='png',dpi=100,bbox_inches='tight')
        plt.close()
        with open('hk_plot.png','rb') as plot:
            self._send_photo(plot)
        return

    def list_channels(self):
        '''
        return a list of all the temperature channels
        '''
        answer = ''

        # entropy
        self._assign_entropy_labels()
        for avs in ['AVS47_1','AVS47_2']:
            for ch in range(8):
                txt='%s_ch%i = %s\n' % (avs,ch,self.entropy_channel_title[avs][ch])
                answer += txt
            answer += '\n'

        # temperature diodes
        for idx,label in enumerate(self.temperature_headings):
            txt = 'TEMPERATURE%02i = %s\n' % (idx+1,label)
            answer += txt

        # heaters
        answer += '\n'
        self._assign_heater_labels()
        for key in self.heater_label.keys():
            answer += '%s = %s\n' % (key,self.heater_label[key])

        self._send_message(answer)
        return
    
    def calsource(self):
        '''
        return the status of the calibration source
        '''
        role = 'bot'
        cli = calsource_configuration_manager(role=role, verbosity=0)
        cli.send_command('status')
        retval = cli.listen_for_acknowledgement(timeout=20) # tstamp is when the info was received
        if retval is None:
            answer = 'No calsource information'
            self._send_message(answer)
            return

        tstamp,ack = retval

        msg_list = ack.decode().split()
        if len(msg_list) < 3:
            answer = 'Calsource calibration configuration unknown\n  response: %s' % ack
            self._send_message(answer)
            return
        
        tstamp0 = float(msg_list[0]) # when info was gathered by PiGPS
        tstamp1 = float(msg_list[1]) # when info was requested by bot

        answer = 'Calsource configuration at %s\n' % dt.datetime.utcfromtimestamp(tstamp0).strftime('%Y-%m-%d %H:%M:%S')
        for item in msg_list[2:]:
    
            cols = item.split(':')
            if len(cols)==1:
                answer += item.ljust(18,' ')+'\n'
                continue
            line = cols[0].ljust(18,' ')
        
            parmval = cols[1].split('=')
            if len(parmval)==1:
                line += ' = '.rjust(23,' ')+parmval[0]
                answer += line+'\n'
                continue
        
            line += parmval[0].rjust(20,' ')+' = '+parmval[1]
            answer += line+'\n'

        self._send_message(answer)
        return

    def ip(self):
        '''
        send the IP address
        '''
        cmd = 'hostname'
        hostname,err = shellcommand(cmd)

        cmd = '/sbin/ifconfig -a'
        msg,err = shellcommand(cmd)

        cmd = '/usr/bin/uptime'
        uptime,err = shellcommand(cmd)
        
        answer = 'IP Address from %s\n\n%s\n\n%s' % (hostname,msg,uptime)

        self._send_message(answer)
        return

    def pt(self):
        '''
        status of the pulse tube compressors
        '''
        ret = check_compressors(verbosity=0)
        self._send_message(ret['message'])
        return

    def diskspace(self):
        '''
        check available disk space
        '''
        ret = check_diskspace(verbosity=0)
        self._send_message(ret['message'])
        return

    def ups(self):
        '''
        send the UPS info
        '''
        info = get_ups_info()
        self._send_message(info['full message'])
        return

    def subscribe(self):
        '''
        subscribe to the list of recipients for alarms
        '''
        known_users = get_TelegramAddresses()
        alarm_recipients = get_alarm_recipients()

        msg = ''
        user = ''
        if self.chat_id in known_users.keys():
            user = known_users[self.chat_id]
            msg = 'Hi %s,\n' % user
            
        if self.chat_id not in alarm_recipients:
            alarm_recipients_file = get_fullpath('telegram-alarm-recipients')
            if alarm_recipients_file is None:
                msg = 'ERROR! Could not find the alarm recipients list.'
                self._send_message(msg)
                return
            h = open(alarm_recipients_file,'a')
            newline = '%s %s\n' % (self.chat_id, user)
            h.write(newline)
            h.close()
            
        
        msg +='You are subscribed to the list of alarm recipients.'
        msg += '\nYou will receive a message in case of problems with the pulse tubes, or with the UPS (220V power supply)'
        self._send_message(msg)
        return

    def unsubscribe(self):
        '''
        remove user from the list of alarm recipients
        '''

        known_users = get_TelegramAddresses()
        alarm_recipients = get_alarm_recipients()

        msg = ''
        user = ''

        if self.chat_id in alarm_recipients:
            alarm_recipients_file = get_fullpath('telegram-alarm-recipients')
            if alarm_recipients_file is None:
                msg = 'ERROR! Could not find the alarm recipients list.'
                self._send_message(msg)
                return
            h = open(alarm_recipients_file,'w')
            if alarm_recipients is None: alarm_recipients = [self.chat_id]
            for chat_id in alarm_recipients:
                if chat_id==self.chat_id: continue
                if chat_id in known_users.keys():
                    newline = '%s %s\n' % (chat_id, known_users[chat_id])
                else:
                    newline = '%s\n' % chat_id
                h.write(newline)
            h.close()
            notmsg = 'no longer'
        else:
            notmsg = 'not'
            
        if self.chat_id in known_users.keys():
            user = known_users[self.chat_id]
            msg = 'Hi %s,\n' % user
        
        msg +='You are %s subscribed to the list of alarm recipients.' % notmsg
        msg += '\nYou will not receive messages in case of problems with the pulse tubes, or with the UPS (220V power supply)'
        self._send_message(msg)
        return


    # def position(self):
    #     '''
    #     get the azimuth and elevation pointing of the platform
    #     '''
    #     az,el,azwarn,elwarn = get_position()
    #     date_str = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    #     if type(az)==str:
    #         az_str = 'ERROR'
    #     else:
    #         if azwarn:
    #             az_str = '%7.2f degrees (possible encoder readout error)' % az
    #         else:
    #             az_str = '%7.2f degrees' % az
                
    #     if type(el)==str:
    #         el_str = 'ERROR'
    #     else:
    #         el_str = '%7.2f degrees' % el
    #     answer = "\nazimuth = %s\nelevation = %s" % (az_str,el_str)
    #     self._send_message(answer)
    #     return

    def position(self):
        '''
        read the mount positions
        '''
        latest_date = dt.datetime.utcfromtimestamp(0)
        fmt_str = '\n%9s:  %.3f degrees'
        answer = 'Pointing:\n'
        for basename in ['AZIMUTH','ELEVATION']:
            fullname = '%s/%s.txt' % (self.hk_dir,basename)
            if not os.path.isfile(fullname):
                continue
        
            h = open(fullname,'r')
            lines = h.read().split('\n')
            h.close()
            lastline = lines[-2]
            cols = lastline.split()
            tstamp = self.timestamp_factor*float(cols[0])
            reading_date = dt.datetime.utcfromtimestamp(tstamp)
            if reading_date > latest_date:
                latest_date = reading_date
            reading = eval(cols[1])
            answer += fmt_str % (basename,reading)

        answer += '\n\nTime: %s' % latest_date.strftime(self.time_fmt)    
        self._send_message(answer)
        return
    

    def _default_answer(self):
        '''
        the default reply to unknown commands
        '''
        ans="I don't understand."
        known_users = get_TelegramAddresses()
        if self.chat_id in known_users.keys():
            ans='Sorry %s, %s' % (known_users[self.chat_id],ans)
        self._send_message(ans)
        return

    def _parseargs(self,args_list):
        '''
        parse the arguments that were sent to the bot
        '''
        self._init_args()
        for arg in args_list:
            print('processing argument: %s' % arg)
            keyarg = arg.split('=')
            if len(keyarg)==2:
                key = keyarg[0].upper()
                if key=='AVS1':key='AVS47_1'
                if key=='AVS2':key='AVS47_2'
                if key=='T' or key=='TEMP':key='TEMPERATURE'
                if key=='MIN' or key=='TMIN': key='YMIN'
                if key=='MAX' or key=='TMAX': key='YMAX'
                if key=='DMIN' or key=='DMAX':
                    print('DEBUG: trying to convert date: %s' % keyarg[1])
                    print('DEBUG: this argument is of type: %s' % type(keyarg[1]))
                    _arg = str2dt( str(keyarg[1]) )
                else:
                    try:
                        _arg = eval(keyarg[1])
                    except:
                        _arg = keyarg[1]
            else:
                key=arg.upper()
                _arg=True
            self.args[key]=_arg

        if self.args['PRESSURE']==True:
            self.args['PRESSURE']=[1]

        for key in self.hktypes:
            if self.args[key]=='':continue
            if not isinstance(self.args[key],list) and not isinstance(self.args[key],tuple):
                self.args[key]=[self.args[key]]
            
        return

    def _respuesta(self,_msg):
        '''
        this is the message receiver
        '''

        if type(_msg)!=dict:
            msg = {}
            msg['msg'] = _msg
            msg['chat'] = {}
            msg['chat']['id'] = _msg
            msg['text'] = 'error message: %s' % _msg
        else:
            msg = _msg

        if 'chat' in msg.keys():
            self.chat_id = msg['chat']['id']
        else:
            self.chat_id = 0xFFFFFFFF

        if 'text' in msg.keys():
            cmd = msg['text']
        else:
            cmd = 'NONE'

        cmd_list = cmd.split()
        if len(cmd_list)>1:
            self._parseargs(cmd_list[1:])

        now=dt.datetime.utcnow()
        user='unknown'
        known_users = get_TelegramAddresses()
        if self.chat_id in known_users.keys():user=known_users[self.chat_id]
        msg="%s %i %16s %s" % (now.strftime(self.time_fmt),self.chat_id, user, cmd)
    
        print(msg)
        h=open('bot.log','a')
        h.write(msg+'\n')
        h.close()

        if len(cmd_list)>0:
            run_cmd = cmd_list[0].lower()
            if run_cmd.find('/')!=0:run_cmd='/'+run_cmd
            if run_cmd in self.commands.keys():
                self.commands[run_cmd]()
            else:
                self._default_answer()
        else:
            self.commands['/start']()
        return



