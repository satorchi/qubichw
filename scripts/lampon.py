#!/usr/bin/env python3
'''
$Id: lampon.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Sun 24 Nov 2019 17:52:31 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

switch on the lamp
'''

# the Energenie powerbar
from PyMS import PMSDevice
e = PMSDevice('energenie','1')
e.set_socket_states({2:True})

