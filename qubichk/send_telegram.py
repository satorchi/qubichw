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

def _get_bot_id(filename=None):
    '''
    get the bot Id information, which is not kept on the GitHub server
    '''
    errflag = False
    botId_file=filename
    if botId_file is None:botId_file='botId.txt'
    if not os.path.isfile(botId_file):
        if 'HOME' not in os.environ.keys():
            print('ERROR! Could not find telebot Id: %s' % botId_file)
            return None                    
        homedir = os.environ['HOME']
        botId_file = '%s/botId.txt' % homedir
        if not os.path.isfile(botId_file):
            print('ERROR! Could not find telebot Id: %s' % botId_file)
            return None
        
    h = open(botId_file,'r')
    line = h.readline()
    h.close()
    botId = line.strip()
    return botId

def send_telegram(msg,chat_id=None):
    '''
    send a message on the Telegram messaging service from the QUBIC bot
    '''
    botId = _get_bot_id()
    if botId is None:
        return False

    if chat_id is None:
        chat_id = 610304074 # Steve
        
    bot = telepot.Bot(botId)

    bot.sendMessage(chat_id,msg)
    return

