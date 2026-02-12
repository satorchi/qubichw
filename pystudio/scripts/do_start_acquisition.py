#!/usr/bin/env python3
'''
$Id: do_start_acquisition.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 12 Feb 2026 11:54:42 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

start an acquisition with the frontend in the current setting
'''
import sys, time
from satorchipy.utilities import parseargs
from pystudio import pystudio

parameterList = ['comment',
                 'title']
options = parseargs(sys.argv,expected_args=parameterList)

def cli():
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    ack = dispatcher.start_acquisition(title=options['title'],comment=options['comment'])
    ack = dispatcher.unsubscribe()
    return

if __name__ == '__main__':
    cli()

