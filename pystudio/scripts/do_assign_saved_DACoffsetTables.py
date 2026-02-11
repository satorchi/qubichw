#!/usr/bin/env python3
'''
$Id: do_assign_saved_DACoffsetTables.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 11 Feb 2026 16:51:31 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

assign the DAC offset tables which are found in ~/.local/share/qubic/DAC-Offset-Table_ASICNN.txt
'''
from pystudio import pystudio

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.assign_saved_DACoffsetTables()
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()


