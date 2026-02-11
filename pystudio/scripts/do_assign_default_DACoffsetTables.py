#!/usr/bin/env python3
'''
$Id: do_assign_default_DACoffsetTables.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 11 Feb 2026 16:56:03 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

assign the default DAC offset values

Note:  This is also done as part of do_init_frontend.py
but in case you want to do it without all the other init actions, you can do it with this script
'''
from pystudio import pystudio

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()

    for asic_num in [1,2]:
        offsetTable = dispatcher.get_default_setting('offsetTable',asic=asic_num)
        ack = dispatcher.send_offsetTable(asic_num,offsetTable)
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()

