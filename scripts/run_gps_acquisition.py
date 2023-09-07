#!/usr/bin/env python3
'''
$Id: run_gps_acquisition.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 07 Sep 2023 08:09:50 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

run the acquisition for the SimpleRTK, ie. the calsource box position and orientation
'''
from qubichw.read_gps import acquire_gps
from qubichk.utilities import shellcommand

cmd = "/sbin/ifconfig eth0 |grep '\<inet\>'|awk '{print $2}'"
ipaddr, err = shellcommand(cmd)

if not ipaddr: ipaddr=None
acquire_gps()
