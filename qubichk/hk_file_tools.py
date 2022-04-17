'''
$Id: hk_file_tools.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 28 Dec 2018 05:27:34 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

tools for reading QUBIC raw housekeeping files
'''
import sys,os,re,time
import datetime as dt
from glob import glob
import numpy as np

def read_temperature_dat(filename):
    '''
    return the date,data from the temperature.dat file
    this is the file generated by the temperature monitoring script by Manual Gonzalez
    '''
    if not os.path.isfile(filename):
        print('ERROR! File not found: %s' % filename)
        return None

    h=open(filename,'r')
    lines=h.read().split('\n')
    h.close()
    del(lines[-1]) # last line is always empty

    headings = re.sub('^#','',lines[0]).split()
    ncols=len(headings)
    del(lines[0])
    npts=len(lines)
    t = -np.ones((npts,ncols))

    for idx,line in enumerate(lines):
        cols=line.split()
        for idx_col,str_val in enumerate(cols):
            t[idx,idx_col]=eval(str_val)

    return headings,t


def read_hk_file(filename):
    '''
    return the date,data from the Housekeeping broadcast file
    '''
    if not os.path.isfile(filename):
        print('ERROR! File not found: %s' % filename)
        return None,None

    h = open(filename,'r')
    lines = h.read().split('\n')
    h.close()
    del(lines[-1])
    npts = len(lines)
    t = np.zeros(npts)
    v = np.zeros(npts)
    onoff = np.zeros(npts,dtype=bool)
    idx=0
    badpattern = re.compile('[a-z][A-Z]')
    for line_idx,line in enumerate(lines):
        cols = line.strip().replace('\x00','').split()
        if len(cols)<2: continue
        if badpattern.match(cols[0]): continue
        if badpattern.match(cols[1]): continue
        try:
            tstamp = float(cols[0])
            reading = eval(cols[1])
            v[idx] = reading
            t[idx] = tstamp
            idx+=1
        except:
            print("ERROR! Couldn't read line: %i) %s" % (line_idx+1,line))
            continue

        if len(cols)<3: continue
        if cols[2]=='ON': onoff[idx] = True
        

    if idx<npts:
        t = t[0:idx]
        v = v[0:idx]
        onoff = onoff[0:idx]
        print('%s: idx,npts = %i,%i' % (filename,idx,npts))
    return t,v,onoff


def read_entropy_label(filename):
    '''                                                                                                      
    read temperature labels from the Entropy Windows machine, shared by Samba
    '''

    if not os.path.isfile(filename):
        print('ERROR! File not found: %s' % filename)
        return None

    chan_str = re.sub('\.log','',os.path.basename(filename))
    match_str = '.* AVS47 (AVS47[-_][12]) Ch ([0-7]) '
    match = re.match(match_str,chan_str)
    chan_str = re.sub(match_str,'',chan_str)
    if match:
        avs=match.group(1).replace('-','_')
        ch=eval(match.group(2))
        if chan_str!='':
            return chan_str

    match_str = '.* AVS47 (AVS47) Ch ([0-7]) '
    match = re.match(match_str,chan_str)
    chan_str = re.sub(match_str,'',chan_str)
    if match:
        avs=match.group(1)+'_1'
        ch=eval(match.group(2))
        if chan_str!='':
            return chan_str

    match = re.match('20[12][0-9]-[01][0-9]-[0-3][0-9] ...... AVS47 (.*)\.log',os.path.basename(filename))
    if match:
        return match.groups()[0]

    match = re.match('20[12][0-9]-[01][0-9]-[0-3][0-9] ...... (.*)\.log',os.path.basename(filename))
    if match:
        return match.groups()[0]

    chan_str = re.sub('\.log','',os.path.basename(filename))
    return 


def read_entropy_logfile(filename):
    '''
    read a temperature log file produced by Entropy
    '''
    if not os.path.exists(filename):
        print('file not found: %s' % filename)
        return None,None
    if not os.path.isfile(filename):
        print('this is not a file: %s' % filename)
        return None,None

    h=open(filename,'r')
    lines=h.read().split('\n')
    h.close()

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
    tdate=np.array(t)
    if tstart>0:
        tdate+=tstart
    val=np.array(val)
    return tdate,val


