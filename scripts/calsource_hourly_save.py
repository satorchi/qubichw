#!/usr/bin/env python3
'''
$Id: calsource_hourly_save.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Tue 30 Apr 2019 07:28:56 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

save the calibration source data regularly

this should be run on qubic-central in directory /archive/calsource/hourly
'''
from qubichw.arduino import arduino

cs = arduino()

while True:
    cs.acquire(3600)

    

