#!/usr/bin/env python3
'''
$Id: mech_openclose.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 04 Dec 2018 22:35:58 CET
$completely_rewritten: Sun 05 Feb 2023 20:07:01 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

open/close the Mechanical heat switches
'''
import sys,os,time
import datetime as dt

from qubichk.entropy_hk import entropy_hk


hk = entropy_hk()
nsteps = 150000 # number of steps to open
nsqueeze = 500  # extra number of steps to squeeze closed a bit more
wait_open = 60  # wait time in seconds before closing again

now = dt.datetime.utcnow()
print('%s | Opening Mechanical Heat Switch' % now.strftime('%Y-%m-%d %H:%M:%S.%f UT'))
hk.mech_command(1,nsteps,'open')

time.sleep(wait_open)
now = dt.datetime.utcnow()            
print('%s | Closing Mechanical Heat Switch' % now.strftime('%Y-%m-%d %H:%M:%S.%f UT'))
hk.mech_command(1,nsteps+nsqueeze,'close')
    
