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

from qubichk.platform import get_position
from qubichk.hwp import get_hwp_info

hk_dir = '/home/qubic/data/temperature/broadcast'
if not os.path.isdir(hk_dir):
    hk_dir = '/home/steve/data/2021/hk'

if not os.path.isdir(hk_dir):
    print('could not find Housekeeping data directory')
    quit()
    
exclude_files = ['TEMPERATURE_RAW.txt',
                 'TEMPERATURE_VOLT.txt',
                 'LABELS.txt',
                 'compressor1_log.txt',
                 'compressor2_log.txt',
                 'ups_log.txt']
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

    tstamp = float(col[0])
    val = float(col[1])
    onoff = None
    if len(col)>2:
        onoff = col[2]
    return tstamp, val, onoff


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
    


# initialize output variables
lines = []
tstamps = []

# first of all, read the platform position directly from socket
labels = ['azimuth','elevation']
vals = get_position()
azel = vals[:2]
warn = vals[2:]
tstamp = dt.datetime.utcnow().timestamp()
date_str = dt.datetime.utcfromtimestamp(tstamp).strftime('%Y-%m-%d %H:%M:%S')
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
date_str = dt.datetime.utcfromtimestamp(tstamp).strftime('%Y-%m-%d %H:%M:%S')
label = 'HWP Position'
line = '%s %s %s' % (date_str, hwpinfo['pos'].rjust(20), label.center(20))
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
        tstamps.append(tstamp)
        date = dt.datetime.utcfromtimestamp(tstamp)
        date_str = date.strftime('%Y-%m-%d %H:%M:%S')
    
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
        lines.append(line)
        if R_str is not None:
            line = '%s %s %s %s' % (date_str, R_str.rjust(20), label.center(20), labelkey)
            lines.append(line)
            
    
# do the rest of the HK files
for F in hk_files:
    basename = os.path.basename(F)
    if basename in exclude_files: continue
    if basename.find('HEATER')==0: continue # already done, above

    retval = read_lastline(F)
    if retval is None: continue
    tstamp,val,onoff = retval
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
    date_str = date.strftime('%Y-%m-%d %H:%M:%S')

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
    if delta>5 or line.find('bad answer')>=0 or line.find('?')>=0:
        lines[idx] = colored(line,'red','on_white')
    


page = '\n'.join(lines)
print(page)


