#!/usr/bin/env python3
'''
$Id: send_telegram.py
$auth: Steve Torchinsky <satorchi@apc.in2p3.fr>
$created: Wed 25 Nov 2020 11:10:47 CET
$license: GPLv3 or later, see https://www.gnu.org/licenses/gpl-3.0.txt

          This is free software: you are free to change and
          redistribute it.  There is NO WARRANTY, to the extent
          permitted by law.

send a message on the Telegram messaging service
'''
import os,sys
import telepot
from qubichk.qubic_bot import get_botId, get_TelegramAddresses

def send_telegram(msg,rx=None):
    '''
    send a message on the Telegram messaging service from the QUBIC bot
    '''
    botId = get_botId()
    if botId is None:return False

    chatid_dict = get_TelegramAddresses()

    # make reverse lookup
    users_dict = {}
    for chatid in chatid_dict.keys():
        users_dict[chatid_dict[chatid]] = chatid
        
    
    bot = telepot.Bot(botId)
    
    if rx is None: rx = 'Steve'
    if rx not in users_dict.keys():
        print('ERROR! Telegram not sent.  Could not find id for user: %s' % rx)

        if 'Steve' not in users_dict.keys():
            print('BIG ERROR!  Could not find id for Steve!')
            return False
        
        bot.sendMessage(users_dict['Steve'],'Trying to send message to unknown user: %s' % rx)
        return False
        
    chatid = users_dict[rx]        
    bot.sendMessage(chatid,msg)
    return True

