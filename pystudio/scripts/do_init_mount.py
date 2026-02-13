#!/usr/bin/env python3
'''
$Id: do_init_mount.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 13 Feb 2026 19:35:36 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

do the initialization commands for the mount PLC
'''
from qubichk.obsmount import obsmount

mount = obsmount()

def cli():
    for axis_name in mount.axis_keys:
        mount.do_command_init(axis_name)
    return

if __name__ == '__main__':
    cli()


