#!/usr/bin/env python3
'''
$Id: modulator_commander.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Fri 25 Jan 2019 11:11:13 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

a command line interface to the TTi 5012A Signal Generator
'''
from qubichw.modulator_tg5012a import tg5012 as modulator

sigmod = modulator()
sigmod.command_loop()
