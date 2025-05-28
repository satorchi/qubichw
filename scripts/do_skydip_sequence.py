#!/usr/bin/env python3
'''
$Id: do_skydip_sequence.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 28 May 2025 11:23:01 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

do the sky dip sequence:  up and down elevation at different azimuth

this script uses the default values
you can change these with:
mount.do_skydip_sequence(azstep=5)

or by changing class variables before running do_skydip_sequence()
for example:

mount = obsmount()
mount.elmin = 50
mount.elmax = 70
mount.azmin = 0
mount.azmax = 15
mount.azstep = 5

'''
from qubichk.obsmount import obsmount

mount = obsmount()
mount.do_skydip_sequence()

