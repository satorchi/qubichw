#!/usr/bin/env python3
'''
$Id: get_frontend_settings.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Thu 21 Aug 2025 14:33:58 CEST
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

get the status of the frontend
'''
import sys
import numpy as np
from pystudio import pystudio

# do the full list to see what we've got.  THIS IS TEMPORARY
# parm_list = list(dispatcher.parameterstable.keys())

# # try to find Aplitude
# parm_list = ['PARAMETER_UNKNOWN_10551_ID',
#              'PARAMETER_UNKNOWN_10552_ID',
#              'PARAMETER_UNKNOWN_10553_ID',
#              'PARAMETER_UNKNOWN_10554_ID',
#              'PARAMETER_UNKNOWN_10555_ID',
#              'PARAMETER_UNKNOWN_10556_ID',
#              'PARAMETER_UNKNOWN_10557_ID',
#              'PARAMETER_UNKNOWN_10558_ID',
#              'PARAMETER_UNKNOWN_10559_ID',
#              'PARAMETER_UNKNOWN_10560_ID']
# not possible.  see email from Wilfried 25 Aug 2025 11:19:25


# if the parameter list is given as an argument, interpet as a comma separated list
parm_list = None
if len(sys.argv)>1:
    parm_list = sys.argv[1].split(',')


def cli():
    '''
    main program to get the frontend status
    '''
    dispatcher = pystudio()
    ack = dispatcher.subscribe_dispatcher()
    msg = dispatcher.get_frontend_settings(parameterList=parm_list)
    print(msg)
    dispatcher.unsubscribe()
    return

if __name__=='__main__':
    cli()
    

