#!/usr/bin/env python3
'''
$Id: compressorstatus.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 24 Nov 2021 16:41:10 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.
check compressor status, and send a Telegram message if not okay
'''
import sys,time

from qubichk.hk_verify import check_compressors
from qubichk.send_telegram import send_telegram

ans = check_compressors(verbosity=0)

# try one more time if there was a communication error
if ans['communication error']:
    time.sleep(0.5)
    ans = check_compressors(verbosity=0)

msg = ans['error_message'] + '\n***********\n' + ans['message']
if not ans['ok'] and not ans['communication error']:
    send_telegram(msg,'Jean-Christophe')
    send_telegram(msg,'Christian')
    send_telegram(msg,'Steve')
if ans['communication error']:
    msg = 'The following message was not sent to JC nor to Christian\n- - - - - -\n'+msg
    send_telegram(msg,'Steve')
    

### testing send telegram to JC
if len(sys.argv)>1 and sys.argv[1]=="--test":
    msg = 'Hi Jean-Christophe!'
    msg += "\nThis is QUBIC.  I hope you are well.  I'm fine."
    msg += "\nI'm just testing the script to check the compressor status."
    msg += "\nI will check the status every five minutes, and if there's a problem, I'll send you a telegram."
    msg += "\nBest regards from your friend,"
    msg += "\nQUBIC"
    msg += "\n\nP.S.  Here's the compressor status:\n\n"
    msg += ans['error_message'] + '\n***********\n' + ans['message']
    send_telegram(msg,'Jean-Christophe')
    send_telegram(msg,'Steve')

    
