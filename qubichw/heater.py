'''
$Id: heater.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 26 Feb 2025 14:00:50 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

heater modes to effectively create slow, mid, and high heater modes by changing the duty cycle
'''
import os,sys,socket
import datetime as dt

# the numato relay for switching on/off
from qubichw.relay import relay



