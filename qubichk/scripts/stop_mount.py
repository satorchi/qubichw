#!/usr/bin/env python3
'''
$Id: stop_mount.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 06 Jun 2025 17:42:37 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

stop the observation mount
'''
from qubichk.obsmount import obsmount
mount = obsmount()
mount.stop()


