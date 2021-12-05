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

def telegram_datafile(filename=None):
    '''
    get the full path to the desired Telegram data file
    filename can be botId.txt or telegram_addressbook
    '''
    search_dirs = []
    if 'XDG_DATA_HOME' in os.environ.keys():
        search_dirs.append('%s/qubic' % os.environ['XDG_DATA_HOME'])
    if 'HOME' in os.environ.keys():
        homedir = os.environ['HOME']        
    else:
        homedir = '/home/qubic'
    search_dirs.append('%s/.local/share/qubic' % homedir)
    search_dirs.append('./')
    search_dirs.append('/home/qubic/.local/share/qubic')

    for d in search_dirs:
        fullpath = '%s/%s' % (d,filename)
        if os.path.isfile(fullpath):
            return fullpath

    return None

def get_botId():
    '''
    get the bot Id information, which is not kept on the GitHub server
    '''
    botId_file = telegram_datafile('botId.txt')
    if botId_file is None:
        print('ERROR! Could not find telebot Id: botId.txt')
        return None

    h = open(botId_file,'r')
    line = h.readline()
    h.close()
    botId = line.strip()
    return botId

def get_TelegramAddresses():
    '''
    read the known chat Id's
    '''
    addrbook_file = telegram_datafile('telegram-addresses')
    if addrbook_file is None: return None

    h = open(addrbook_file,'r')
    lines = h.read().split('\n')
    h.close()
    del(lines[-1])
    known_users = {}
    for line in lines:
        id_str,user_str = line.split(':')
        chatid = int(id_str.strip())
        user = user_str.strip()
        known_users[chatid] = user

    return known_users

def get_alarm_recipients():
    '''
    read the list of alarm recipients
    '''
    rx_file = telegram_datafile('telegram-alarm-recipients')
    if rx_file is None: return ['Steve']

    h = open(rx_file,'r')
    lines = h.read().split('\n')
    h.close()
    del(lines[-1])
    alarm_recipients = []
    for line in lines:
        alarm_recipients.append(line.strip())

    return alarm_recipients
    

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

    # check for message size.  There is a Telegram limit of 4096 bytes
    if len(msg)<=4096:
        bot.sendMessage(chatid,msg)
        return True

    max_msg_len = 2048
    msg_lines = msg.split('\n')
    msg_list = []
    byte_count = 0
    line_start = 0
    for line_idx,line in enumerate(msg_lines):
        byte_count += len(line)
        if byte_count>=max_msg_len:
            msg_part = '\n'.join(msg_lines[line_start:line_idx])
            bot.sendMessage(chatid,msg_part)
            line_start = line_idx
            byte_count = 0
                     
    return True

