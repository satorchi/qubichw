#!/usr/bin/env python3
'''
$Id: run_calibration_source.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 29 Jan 2019 14:19:05 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

run a measurement with the calibration source
  - switch on calibration source, modulator, amplifier, and arduino
  - configure modulator, calibration source
  - acquire data using the arduino
'''
import os,sys,time
import datetime as dt

msg = '\nHello!\n  This is a test script to run a single acquisition with the calibration source.'
msg += "\n\nAre you sure you don't want to run the calsource_commander.py instead?\n\n"
print(msg)


def helptxt():
    '''
    some help text
    '''
    print('usage: %s duration=<duration in seconds>' % sys.argv[0])
    return


# parse arguments
# read the duration if given
duration_seconds = None
for arg in sys.argv:
    arg = arg.upper()
    if arg.find('DURATION=')==0:
        vals = arg.split('=')
        try:
            duration_seconds = eval(vals[1])
        except:
            print('unable to read duration.')
        continue

    # maybe the duration was given on its own without the prefix "duration="
    if duration_seconds is None:
        try:
            duration_seconds = eval(arg)
        except:
            pass
        
        
if duration_seconds is None:
    helptxt()
    quit()


# qubichw tools for commanding various hardware
from qubichw.modulator_tg5012a import tg5012 as modulator
from qubichw.arduino import arduino
from qubichw.calibration_source import calibration_source

# this is for the Energenie smart powerbar to switch on/off the devices
from PyMS import PMSDevice
energenie = PMSDevice('energenie', '1')

energenie_socket = {}
energenie_socket['modulator'] = 0
energenie_socket['calibration source'] = 1
energenie_socket['lamp'] = 2
energenie_socket['amplifier'] = 3

'''
THIS IS NOT WORKING.  IT HANGS AFTER THE FIRST SWITCH-ON
# switch on devices
for dev in ['amplifier','modulator','calibration source']:
    print('switching on %s' % dev)
    energenie.set_socket_states({energenie_socket[dev]:True})
    print('pause for 1 second')
    time.sleep(1)
'''
    
# initialize devices
print('initializing modulator')
mod = modulator()
mod.configure(frequency=0.33,duty=33)

print('initializing calibration source')
calsrc = calibration_source('LF')
calsrc.set_Frequency(150)

print('initializing arduino')
ard = arduino()
ard.init()

# make an acquisition
startTime = dt.datetime.utcnow()
print('acquisition will begin now and continue for %.1f seconds' % duration_seconds)
t,v = ard.acquire(duration=duration_seconds)

# write the result to file
outfile = startTime.strftime('calsource_%Y%m%dT%H%M%S.dat')
h=open(outfile,'w')
for idx,val in enumerate(v):
    tstamp = t[idx].strftime('%s.%f')
    h.write('%s %i\n' % (tstamp,val))
h.close()
print('output file written: %s' % outfile)


