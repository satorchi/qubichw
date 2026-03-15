#!/usr/bin/env python3
'''
$Id: run_obsmount_rebroadcaster.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Sun 15 Mar 2026 19:59:29 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

run the observation mount rebroadcaster service
'''
from qubichk.obsmount import obsmount
mount = obsmount()
ack = mount.listen_for_command()
