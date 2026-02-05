#!/usr/bin/env python3
'''
$Id: do_end_observation.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 05 Feb 2026 19:33:20 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

end an ongoing observation
'''
from pystudio import pystudio


def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.end_observation()
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()


