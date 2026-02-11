#!/usr/bin/env python3
'''
$Id: do_park_frontend.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 11 Feb 2026 17:23:20 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

put the frontend into "parking" settings
sine bias with amplitude 1V and offset 8V
stop regulations
stop MGC3 temperature feedback loop
'''
from pystudio import pystudio

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.park_frontend()
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()


