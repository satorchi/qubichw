#!/usr/bin/env python3
'''
$Id: show_hk.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 18 Nov 2021 13:13:45 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

show the latest housekeeping values on screen

text highlighting from: https://stackoverflow.com/questions/5947742/how-to-change-the-output-color-of-echo-in-linux
'''
import sys,os
from glob import glob
import datetime as dt
from termcolor import colored
from satorchipy.datefunctions import str2dt
from qubichk.platform import get_position
from qubichk.hwp import get_hwp_info

hk_dir = '/home/qubic/data/temperature/broadcast'
if not os.path.isdir(hk_dir):
    hk_dir = '/home/steve/data/2022/hk'

if not os.path.isdir(hk_dir):
    print('could not find Housekeeping data directory')
    quit()

date_fmt = '%Y-%m-%d %H:%M:%S'    
exclude_files = ['TEMPERATURE_RAW.txt',
                 'TEMPERATURE_VOLT.txt',
                 'LABELS.txt',
                 'compressor1_log.txt',
                 'compressor2_log.txt',
                 'ups_log.txt',
                 'weather.txt']
touchname = 'AVS47_1_ch0.txt'

def read_labels():
    '''
    read the sensor labels
    '''
    labels = {}
    
    labelfile = hk_dir+os.sep+'LABELS.txt'
    if os.path.isfile(labelfile):
        h = open(labelfile,'r')
        lines = h.read().split('\n')
        del(lines[-1])
        for line in lines:
            col = line.split('=')
            if len(col)<2: continue
            key = col[0].strip()
            val = col[1].strip()
            labels[key] = val
        h.close()

    heaterfile = os.environ['HOME']+os.sep+'powersupply.conf'
    if not os.path.isfile(heaterfile): return labels

    h = open(heaterfile,'r')
    lines = h.read().split('\n')
    del(lines[-1])
    for line in lines:
        col = line.split(':')
        if len(col)<2: continue
        for ext in ['','_Volt','_Amp']:
            key = col[0].strip()+ext
            val = col[1].strip()
            labels[key] = val
    h.close()
    return labels
    
def read_lastline(filename):
    '''
    read the last line of a file
    '''
    
    if not os.path.isfile(filename):
        print('File not found: %s' % filename)
        return None

    h = open(filename,'r')
    nbytes = h.seek(0,os.SEEK_END)
    near_end = nbytes - 4096
    if near_end<0: near_end=0
    h.seek(near_end,0)
    lines = h.read().split('\n')
    h.close()
    if len(lines)<2:
        lastline = lines[0]
    else:
        lastline = lines[-2]

    col = lastline.split()
    if len(col)<2:
        print('Unexpected string: %s' % lastline)
        return None

    val_list = []
    for val_str in col:
        try:
            val = eval(val_str)
        except:
            val = val_str
        val_list.append(val)
            
    if len(col)<3:
        return val_list + [None]

    return val_list


def assign_val_string(val,units):
    if abs(val)>=1:
        val_str = '%7.3f %s' % (val,units)
    elif abs(val)>=1e-3:
        val_str = '%7.3f m%s' % (val*1e3,units)
    elif abs(val)>=1e-6:
        val_str = '%7.3f u%s' % (val*1e6,units)
    elif abs(val)>=1e-9:
        val_str = '%7.3f n%s' % (val*1e9,units)
    elif abs(val)>=1e-12:
        val_str = '%7.3f p%s' % (val*1e12,units)
    else:
        val_str = '%12.5e %s' % (val,units)
    return val_str
    
def read_weather():
    '''
    return a list timestamps, and a list of strings with the weather data
    '''
    basename = 'weather.txt'
    rootname = basename.replace('.txt','')
    weather_file = '%s%s%s' % (hk_dir,os.sep,basename)
    vals = read_lastline(weather_file)
    if vals is None: return None

    lines = []
    tstamps = []

    tstamp = vals[0]
    tstamps.append(tstamp)
    date_str = dt.datetime.utcfromtimestamp(tstamp).strftime(date_fmt)
    val_str = '%.1f C' % vals[1]
    label = 'outside temperature'
    line = '%s %s %s %s' % (date_str, val_str.rjust(20), label.center(20), rootname)
    lines.append(line)

    tstamps.append(tstamp)
    val_str = '%.1f %%' % vals[2]
    label = 'relative humidity'
    line = '%s %s %s %s' % (date_str, val_str.rjust(20), label.center(20), rootname)
    lines.append(line)
    
    return tstamps,lines

def read_ups():
    '''
    return a list of timestamps and a list of strings with the UPS status
    '''
    basename = 'ups_log.txt'
    rootname = basename.replace('.txt','')
    ups_file = '%s%s%s' % (hk_dir,os.sep,basename)
    vals = read_lastline(ups_file)
    if vals is None: return None

    lines = []
    tstamps = []

    date = str2dt(vals[0])
    tstamp = date.timestamp()
    date_str = date.strftime(date_fmt)

    label = 'input voltage'
    tstamps.append(tstamp)
    if vals[1].find(label.replace(' ','.'))<0:
        val_str = 'NO UPS INFO'
    else:
        val = eval(vals[1].split('=')[-1])
        val_str = '%.1f VAC' % val
        if val<210: label+=' LOW!'
    line = '%s %s %s %s' % (date_str, val_str.rjust(20), label.center(20), rootname)
    lines.append(line)

    
    label = 'battery charge'
    tstamps.append(tstamp)
    if vals[2].find(label.replace(' ','.'))<0:
        val_str = 'NO UPS INFO'
    else:
        val = eval(vals[2].split('=')[-1])
        val_str = '%.1f %%' % val
        if val<50: label+=' LOW!'
    line = '%s %s %s %s' % (date_str, val_str.rjust(20), label.center(20), rootname)
    lines.append(line)
    
    return tstamps,lines

def read_compressor(compressor_num):
    '''
    get the compressor status from the log file
    '''
    basename = 'compressor%i_log.txt' % compressor_num
    rootname = basename.replace('.txt','')
    compressor_file = '%s%s%s' % (hk_dir,os.sep,basename)
    vals = read_lastline(compressor_file)
    if vals is None: return None

    lines = []
    tstamps = []

    date = str2dt(vals[0])
    tstamp = date.timestamp()
    date_str = date.strftime(date_fmt)

    lastline = ' '.join(vals)
    if lastline.find('OFFLINE')>0 or len(vals)<6:
        val_str = 'OFFLINE'
        label_human = 'compressor %i' % compressor_num
        line = '%s %s %s %s' % (date_str, val_str.rjust(20), label_human.center(20), rootname)
        return [tstamp],[line]

    label_human = 'output water'
    label = 'Tout'
    col = vals[4]
    tstamps.append(tstamp)
    if col.find(label)<0:
        val_str = 'NO COMPRESSOR INFO'
    else:
        val = eval(col.split('=')[-1])
        val_str = '%.1f C' % val
    line = '%s %s %s %s' % (date_str, val_str.rjust(20), label_human.center(20), rootname)
    lines.append(line)

    
    label_human = 'intake water'
    label = 'Tin'
    col = vals[5]
    tstamps.append(tstamp)
    if col.find(label)<0:
        val_str = 'NO COMPRESSOR INFO'
    else:
        val = eval(col.split('=')[-1])
        val_str = '%.1f C' % val
    line = '%s %s %s %s' % (date_str, val_str.rjust(20), label_human.center(20), rootname)
    lines.append(line)
    
    return tstamps,lines
    
    

# first look at the weather
retval = read_weather()
if retval is None:
    lines = []
    tstamps = []
else:
    tstamps,lines = retval

# read the UPS status
retval = read_ups()
if retval is not None:
    tstamps += retval[0]
    lines += retval[1]

# read the compressor status    
retval = read_compressor(1)
if retval is not None:
    tstamps += retval[0]
    lines += retval[1]
retval = read_compressor(2)
if retval is not None:
    tstamps += retval[0]
    lines += retval[1]

    
# read the platform position directly from socket
labels = ['azimuth','elevation']
vals = get_position()
azel = vals[:2]
warn = vals[2:]
tstamp = dt.datetime.utcnow().timestamp()
date_str = dt.datetime.utcfromtimestamp(tstamp).strftime(date_fmt)
for idx,val in enumerate(azel):
    if type(val)==str:
        val_str = val.center(7)
    else:
        val_str = '%7.2f degrees' % val
    if warn[idx]:
        val_str += ' ?'
    label = labels[idx]
    line = '%s %s %s' % (date_str, val_str.rjust(20), label.center(20))
    lines.append(line)
    tstamps.append(tstamp)

# next read the HWP position
hwpinfo = get_hwp_info()
tstamp = dt.datetime.utcnow().timestamp()
date_str = dt.datetime.utcfromtimestamp(tstamp).strftime(date_fmt)
label = 'HWP Position'
if hwpinfo['pos'] is None:
    hwppos_str = 'UNKNOWN'
else:
    hwppos_str = hwpinfo['pos']
line = '%s %s %s' % (date_str, hwppos_str.rjust(20), label.center(20))
lines.append(line)
tstamps.append(tstamp)


# read latest values saved to HK files
labels = read_labels()

# find all the existing HK files
hk_files = glob(hk_dir+os.sep+'*.txt')
hk_files.sort()


# treat the heaters first
heaterfiletypes = ['Amp','Volt']
heaterunits = {'Volt':'V', 'Amp': 'A'}
for idx in range(7):
    counter = idx + 1
    heatervals = {}

    for filetype in heaterfiletypes:
        basename = 'HEATER%i_%s.txt' % (counter,filetype)
        F = '%s%s%s' % (hk_dir,os.sep,basename)
        if not os.path.isfile(F): continue
    
        retval = read_lastline(F)
        if retval is None: continue
        tstamp,val,onoff = retval
        date = dt.datetime.utcfromtimestamp(tstamp)
        date_str = date.strftime(date_fmt)
    
        label = ''
        labelkey = basename.replace('.txt','')
        if labelkey in labels.keys():
            label = labels[labelkey]

        units = heaterunits[filetype]
        if filetype=='Amp':
            if onoff is not None and onoff=='OFF': continue # don't print the current if the powersupply is off
            units = 'A'
            val *= 0.001
        else:
            units = 'V'
        heatervals[filetype] = val

        R_str = None
        if onoff is not None and onoff=='OFF':
            units += ' OFF'
        elif 'Volt' in heatervals.keys() and 'Amp' in heatervals.keys() and heatervals['Amp']!=0:
            R = heatervals['Volt']/heatervals['Amp']
            R_str = assign_val_string(R,'Ohm')
        else:
            R_str = None
            

        val_str = assign_val_string(val,units)
        line = '%s %s %s %s' % (date_str, val_str.rjust(20), label.center(20), labelkey)
        tstamps.append(tstamp)
        lines.append(line)
        if R_str is not None:
            line = '%s %s %s %s' % (date_str, R_str.rjust(20), label.center(20), labelkey)
            tstamps.append(tstamp)
            lines.append(line)
            
    
# do the rest of the HK files
for F in hk_files:
    basename = os.path.basename(F)
    if basename in exclude_files: continue
    if basename.find('HEATER')==0: continue # already done, above

    retval = read_lastline(F)
    if retval is None: continue
    tstamp,val,onoff = retval
    if val=='inf': val=1e6
    tstamps.append(tstamp)

    label = ''
    labelkey = basename.replace('.txt','')
    if labelkey in labels.keys():
        label = labels[labelkey]


    units = None
    val_str = None
    if basename==touchname:
        units = 'Ohm'
    elif basename.find('TEMPERATURE')==0 or basename.find('AVS')==0:
        units = 'K'
    elif basename.find('PRESSURE')==0:
        units = 'bar'
        val *= 0.001
    elif basename.find('Volt')>0:
        units = 'V'
    elif basename.find('Amp')>0:
        if onoff is not None and onoff=='OFF':
            units = ''
            val_str = 'OFF'
        else:
            units = 'A'
            val *= 0.001
    elif basename.find('MHS')==0:
        units = 'steps'
    else:
        units = ''
        
    date = dt.datetime.utcfromtimestamp(tstamp)
    date_str = date.strftime(date_fmt)

    if units == 'steps':
        val_str = '%10i %s' % (int(val), units)
        
    if val_str is None:
        val_str = assign_val_string(val,units)


    line = '%s %s %s %s' % (date_str, val_str.rjust(20), label.center(20), labelkey)
    lines.append(line)


latest = max(tstamps)
n_tstamps = len(tstamps)
for idx,line in enumerate(lines):
    if idx>=n_tstamps: break
    delta = latest - tstamps[idx]
    limit_delta = 7
    if line.find('ups')>0:
        limit_delta=67
    if delta>limit_delta or line.find('bad answer')>=0 or line.find('?')>=0 or line.find('LOW!')>=0 or line.find('NO UPS')>=0:
        lines[idx] = colored(line,'red','on_white')


page = '\n'.join(lines)
print(page)


